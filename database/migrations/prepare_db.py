#!/usr/bin/env python3
import os
import sys
import argparse
import glob
from typing import Iterable, List, Optional

import psycopg2
from psycopg2.extensions import connection as PGConnection


def load_dotenv(path: str) -> None:
    """
    Charge un .env simple (KEY=VALUE par ligne) dans l'environnement courant.
    Les lignes vides et celles commençant par # sont ignorées.
    """
    if not path or not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


def get_pg_conn_from_env() -> PGConnection:
    """
    Supporte à la fois les noms 'psycopg2' (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD)
    et les alias style .env fournis (PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD).
    """
    host = os.getenv("PGHOST") or os.getenv("PG_HOST", "localhost")
    port = os.getenv("PGPORT") or os.getenv("PG_PORT", "5432")
    db   = os.getenv("PGDATABASE") or os.getenv("PG_DB", "postgres")
    user = os.getenv("PGUSER") or os.getenv("PG_USER", "postgres")
    pwd  = os.getenv("PGPASSWORD") or os.getenv("PG_PASSWORD", "")
    ssl  = os.getenv("PGSSLMODE", "disable")

    dsn = f"host={host} port={port} dbname={db} user={user}"
    if pwd:
        dsn += f" password={pwd}"
    if ssl:
        dsn += f" sslmode={ssl}"

    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False
        return conn
    except Exception as e:
        raise RuntimeError(f"Connexion PostgreSQL échouée: {e}") from e


def table_has_rows(conn: PGConnection, table: str) -> bool:
    """
    Retourne True si la table existe ET contient au moins 1 ligne.
    Si la table n'existe pas, retourne False.
    """
    q_exists = """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema = 'public'
            AND table_name = %s
        )
    """
    with conn.cursor() as cur:
        cur.execute(q_exists, (table,))
        exists = cur.fetchone()[0]
        if not exists:
            return False

    q_has = f"SELECT 1 FROM public.{table} LIMIT 1"
    try:
        with conn.cursor() as cur:
            cur.execute(q_has)
            row = cur.fetchone()
            return row is not None
    except Exception:
        # Si la table existe mais est inaccessible pour une raison quelconque
        return False


def any_table_non_empty(conn: PGConnection, tables: Iterable[str]) -> List[str]:
    """
    Renvoie la liste des tables (parmi 'tables') qui contiennent des lignes.
    Si la table n'existe pas ou est vide, elle n'est pas listée.
    """
    non_empty = []
    for t in tables:
        t_norm = t.strip()
        if not t_norm:
            continue
        if table_has_rows(conn, t_norm):
            non_empty.append(t_norm)
    return non_empty


def run_sql_file(conn: PGConnection, path: str) -> None:
    """
    Exécute **tout** le contenu d'un fichier .sql dans une transaction.
    En cas d'erreur, rollback sur ce fichier et relance l'exception.
    """
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"✅ Applied: {os.path.basename(path)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR in {os.path.basename(path)}: {e}")
        raise


def run_all_migrations(conn: PGConnection, sql_dir: str) -> None:
    """
    Exécute tous les *.sql du répertoire (ordre alphabétique).
    Ignoré si aucun fichier.
    """
    files = sorted(glob.glob(os.path.join(sql_dir, "*.sql")))
    if not files:
        print(f"ℹ️  Aucun fichier .sql trouvé dans {sql_dir} — rien à appliquer.")
        return
    print(f"📚 {len(files)} fichier(s) .sql à appliquer depuis {sql_dir} ...")
    for fp in files:
        run_sql_file(conn, fp)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Prépare la base (DDL) si toutes les tables listées sont vides (ou absentes)."
    )
    p.add_argument(
        "--env",
        dest="env_file",
        help="Chemin du fichier .env à charger (facultatif).",
        default=None,
    )
    p.add_argument(
        "--sql-dir",
        dest="sql_dir",
        help="Répertoire contenant les .sql (défaut: migrations/sql).",
        default=os.path.join(os.path.dirname(__file__), "sql"),
    )
    p.add_argument(
        "--tables",
        dest="tables",
        help=(
            "Liste des tables à contrôler, séparées par des virgules. "
            "Si au moins une est non vide, on s'arrête. "
            "Défaut: lufthansa_flight_history,weather_hourly_cache,aircrafts,airlines,airports,countries,routes"
        ),
        default="lufthansa_flight_history,weather_hourly_cache,aircrafts,airlines,airports,countries,routes",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 1) Charger .env si fourni
    if args.env_file:
        print(f"🔧 Chargement .env: {args.env_file}")
        load_dotenv(args.env_file)

    # 2) Connexion
    print("🔌 Connexion à PostgreSQL ...")
    conn = get_pg_conn_from_env()

    # 3) Vérifier tables vides / non vides
    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    print(f"🔎 Contrôle des tables: {', '.join(tables)}")
    non_empty = any_table_non_empty(conn, tables)

    if non_empty:
        print("🛑 Arrêt : les tables suivantes contiennent déjà des données :")
        for t in non_empty:
            print(f"   - {t}")
        print("ℹ️  Aucune migration n'a été exécutée.")
        conn.close()
        sys.exit(0)

    print("✅ OK : toutes les tables sont absentes ou vides → exécution des migrations DDL.")
    # 4) Exécuter les migrations SQL
    run_all_migrations(conn, args.sql_dir)

    conn.close()
    print("🎉 Préparation terminée.")


if __name__ == "__main__":
    main()