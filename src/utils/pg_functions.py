import os
from contextlib import contextmanager
from datetime import date, timedelta
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import MetaData, Table
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from config.env_loader import load_env

load_env()


FK_VIOLATION_CODE = "23503"

HOST = os.getenv("PG_HOST")
PORT = int(os.getenv("PG_PORT"))
DBNAME = os.getenv("PG_DB")
USER = os.getenv("PG_USER")
PASSWORD = os.getenv("PG_PASSWORD")

# URL-encode the password to handle special characters
PASSWORD_ENCODED = quote_plus(PASSWORD)

# Connexion PostgreSQL with properly encoded password
DB_URL = f"postgresql://{USER}:{PASSWORD_ENCODED}@{HOST}:{PORT}/{DBNAME}"
engine = create_engine(DB_URL)

@contextmanager
def _begin_conn(engine):
    """Contexte pratique pour obtenir une connexion et un begin() explicite."""
    with engine.connect() as conn:
        with conn.begin():
            yield conn

def _is_fk_violation(err: IntegrityError) -> bool:
    """Détermine si l'erreur est une violation de clé étrangère (SQLSTATE 23503)."""
    # SQLAlchemy -> .orig peut être une exception psycopg2/psycopg3
    orig = getattr(err, "orig", None)
    # psycopg3: orig.sqlstate ; psycopg2: orig.pgcode
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return code == FK_VIOLATION_CODE

def _progress(start_idx: int, end_idx: int, total: int, msg: str):
    print(f"{msg}  ({start_idx+1}–{end_idx} / {total})")

def insert_dataframe(df, table_name, batch_size: int = 5000):
    if df.empty:
        print(f"Aucune donnée à insérer pour {table_name}")
        return

    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)

    total_rows = len(df)
    inserted_ok = 0
    skipped_fk = 0

    print(f"\nInsertion par lots de {batch_size} lignes dans {table_name}...\n")

    # 1) Chemin rapide: tentative par lot
    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        batch = df.iloc[start:end].to_dict(orient="records")

        try:
            stmt = pg_insert(table).values(batch).on_conflict_do_nothing()
            with _begin_conn(engine) as conn:
                conn.execute(stmt)
            inserted_ok += len(batch)
            _progress(start, end, total_rows, "[OK] Lot traité (doublons ignorés)")
        except IntegrityError as e:
            # Si ce n'est PAS une FK violation, on log et continue en repli ligne à ligne quand même.
            print(f"[WARNING] Conflit d'intégrité sur le lot {start+1}–{end} : {e}. "
                  f"Repli en insertion ligne à ligne avec SAVEPOINT…")

            # 2) Repli sélectif: ligne par ligne avec SAVEPOINT
            with engine.connect() as conn:
                # On gère manuellement les transactions pour pouvoir utiliser des SAVEPOINTs.
                trans = conn.begin()
                try:
                    # Préparer le statement une seule fois pour performance
                    base_stmt = pg_insert(table).on_conflict_do_nothing()

                    for i, row in enumerate(batch, start=start):
                        savepoint = conn.begin_nested()  # crée un SAVEPOINT
                        try:
                            conn.execute(base_stmt.values(row))
                            inserted_ok += 1
                        except IntegrityError as row_err:
                            if _is_fk_violation(row_err):
                                skipped_fk += 1
                                print(f"   ↳ [SKIP] Ligne {i+1} ignorée (ForeignKeyViolation 23503)")
                            else:
                                # Autre violation: on ignore aussi cette ligne mais on l’indique.
                                print(f"   ↳ [SKIP] Ligne {i+1} ignorée (IntegrityError: {row_err})")
                            # rollback au SAVEPOINT pour annuler uniquement cette ligne
                            savepoint.rollback()
                        else:
                            savepoint.commit()
                    trans.commit()
                except Exception as fatal:
                    trans.rollback()
                    print(f"[ERROR] Erreur inattendue lors du repli ligne à ligne: {fatal}")

    print(f"[SUCCESS] Traitement terminé pour {table_name} :")
    print(f"   - Lignes insérées/traitées (hors doublons) : {inserted_ok}")
    print(f"   - Lignes ignorées pour ForeignKeyViolation : {skipped_fk}")

def getImportantRoutes(target_date=None):
    if target_date is None:
        target_date = date.today() - timedelta(days=2)

    query = """
    SELECT r.id, r.departure_airport, r.arrival_airport
    FROM routes r
    WHERE important = TRUE
      AND NOT EXISTS (
        SELECT 1
        FROM lufthansa_flight_history f
        WHERE f.route_id = r.id
          AND f.departure_schedule_date = %(date)s
      )
    """

    return pd.read_sql(query, con=engine, params={"date": target_date})


def getAllImportantRoutes():
    query = text("""
        SELECT id, departure_airport, arrival_airport
        FROM routes
        WHERE important = TRUE
    """)
    return pd.read_sql(query, con=engine)


def getAllLufthansaFlightHistory():
    query = """
    SELECT * FROM lufthansa_flight_history
    """
    return pd.read_sql(query, con=engine)

# Lufthansa Group airlines - only these are supported by the flight status API
LUFTHANSA_GROUP_AIRLINES = ('LH', 'LX', 'OS', 'SN', 'EW', '4Y', 'EN', 'CL', 'WK')


def getFlightsToUpdateToday():
    """
    Retourne les vols dont l'arrivée planifiée est aujourd'hui ET qui n'ont pas encore été rafraîchis.

    Note: Only Lufthansa Group airlines (LH, LX, OS, SN, EW, 4Y, EN, CL, WK) are fetched
    because the Lufthansa flight status API only supports these carriers.
    """
    query = """
    SELECT *
    FROM lufthansa_flight_history
    WHERE arrival_schedule_date = CURRENT_DATE
      AND actuals_refreshed = false
      AND marketing_carrier_airline_id IN ('LH', 'LX', 'OS', 'SN', 'EW', '4Y', 'EN', 'CL', 'WK')
    """
    return pd.read_sql(query, con=engine)


def getFlightsToUpdate(days: int = 7):
    """
    Retourne les vols des N derniers jours qui n'ont pas encore été rafraîchis.

    Note: Only Lufthansa Group airlines (LH, LX, OS, SN, EW, 4Y, EN, CL, WK) are fetched
    because the Lufthansa flight status API only supports these carriers.
    Other airlines (codeshares like UA, DL, AA) appear in schedules but cannot be
    queried for actual flight status.
    """
    query = f"""
    SELECT *
    FROM lufthansa_flight_history
    WHERE departure_schedule_date >= CURRENT_DATE - INTERVAL '{days} days'
      AND departure_schedule_date <= CURRENT_DATE
      AND actuals_refreshed = false
      AND marketing_carrier_airline_id IN ('LH', 'LX', 'OS', 'SN', 'EW', '4Y', 'EN', 'CL', 'WK')
    ORDER BY departure_schedule_date DESC
    """
    return pd.read_sql(query, con=engine)

def get_route_airports(route_id: int):
    """
    Retourne (departure_airport, arrival_airport) pour une route donnée.
    Suppose table routes(id, departure_airport, arrival_airport).
    """
    query = """
        SELECT departure_airport, arrival_airport
        FROM routes
        WHERE id = :rid
        LIMIT 1
    """
    with engine.connect() as conn:
        row = conn.execute(text(query), {"rid": route_id}).fetchone()
        if row:
            return row[0], row[1]
    return None, None

def city_exists(code):
    """Vérifie si une ville existe déjà dans la table cities"""
    if not code:
        return False
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM cities WHERE city_code = :code"), {"code": code})
        return result.fetchone() is not None

def build_historical_flights_from_bts():
    df = pd.read_sql("SELECT * FROM bts_flight_history", engine)

    # Construction des données pour historical_flights
    flights = []

    """
        => df.iterrows()	Méthode Pandas qui retourne un générateur de paires (index, row) où :
                • index est l'index de la ligne
                • row est un objet Series représentant la ligne
        => for _, row in ...
            La variable _ capte l'index, mais on ne s'en sert pas, donc on le nomme _ par convention
        => row
            Est une ligne du DataFrame sous forme de dictionnaire Pandas (row["colonne"])
    """
    for _, row in df.iterrows():
        flights.append({
            "source": "BTS",
            "delay_minutes": int(row['arr_delay']) if not pd.isna(row['arr_delay']) else None,
            "is_delayed": bool(row['arr_del15']) if not pd.isna(row['arr_del15']) and row['arr_del15'] > 0 else False,
            "bts_flight_history_id": row['id']
        })

    flights_df = pd.DataFrame(flights)
    insert_dataframe(flights_df, "historical_flights")

def getAirPorts():
    query = """
    SELECT iata_code, latitude, longitude 
    FROM airports 
    WHERE location_type = 'Airport' 
    AND latitude IS NOT NULL AND longitude IS NOT NULL
    """
    return pd.read_sql(query, engine)

def ensure_airline_exists(airline_code):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM airlines WHERE airline_code = :code LIMIT 1"),
            {"code": airline_code}
        ).fetchone()

    if not result:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO airlines (airline_code) VALUES (:code)"),
                {"code": airline_code}
            )

def ensure_aircraft_exists(aircraft_code):
    if not aircraft_code:
        return

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM aircrafts WHERE aircraft_code = :code LIMIT 1"),
            {"code": aircraft_code}
        ).fetchone()

    if not result:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO aircrafts (aircraft_code) VALUES (:code)"),
                {"code": aircraft_code}
            )

def table_count(table_name: str) -> int:
    q = text(f"SELECT COUNT(*) FROM {table_name}")
    with engine.connect() as conn:
        return int(conn.execute(q).scalar() or 0)