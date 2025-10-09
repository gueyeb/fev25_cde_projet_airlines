import os
import sys
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config.env_loader import load_env

import psycopg2
from psycopg2.extras import execute_values

# Reuse DB/API helpers
from functions.weather_functions import (
    get_airport_from_postgres_byAirPortCode,
    fetch_hourly_series,
    owm_budget_remaining,   # <-- budget restant journalier (UTC) côté DB
)

load_env()

# Connexion DB : même style que ton projet
PG_CONN_INFO = {
    "host":     os.getenv("PG_HOST", "localhost"),
    "port":     int(os.getenv("PG_PORT", "5432")),
    "dbname":   os.getenv("PG_DB", "airline"),
    "user":     os.getenv("PG_USER", "dst_user"),
    "password": os.getenv("PG_PASSWORD", "dst_password"),
}

def getenv_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        print(f"[warn] {name} invalide: {val!r} → fallback {default}")
        return default

OWM_DAILY_BUDGET = getenv_int("OWM_DAILY_BUDGET", 1000)


def _pairs_to_prefill_for_date(cur, target_date):
    """
    Retourne un set {(iata, day_local_00h: timestamptz)} pour:
      - départs SANS météo, ce jour
      - arrivées SANS météo, ce jour
    """
    pairs = set()

    # Départs
    cur.execute(
        """
        SELECT DISTINCT a.iata_code AS iata,
               date_trunc('day',
                 make_timestamptz(
                   EXTRACT(YEAR  FROM lfh.departure_schedule_date)::int,
                   EXTRACT(MONTH FROM lfh.departure_schedule_date)::int,
                   EXTRACT(DAY   FROM lfh.departure_schedule_date)::int,
                   0,0,0,
                   a.timezone
                 )::timestamptz
               ) AS day_local
        FROM lufthansa_flight_history lfh
        JOIN routes r   ON r.id = lfh.route_id
        JOIN airports a ON a.iata_code = r.departure_airport
        WHERE lfh.depart_airport_meteo IS NULL
          AND lfh.departure_schedule_date = %s
        """,
        (target_date,)
    )
    for iata, day_local in cur.fetchall():
        pairs.add((iata, day_local))

    # Arrivées
    cur.execute(
        """
        SELECT DISTINCT a.iata_code AS iata,
               date_trunc('day',
                 make_timestamptz(
                   EXTRACT(YEAR  FROM lfh.arrival_schedule_date)::int,
                   EXTRACT(MONTH FROM lfh.arrival_schedule_date)::int,
                   EXTRACT(DAY   FROM lfh.arrival_schedule_date)::int,
                   0,0,0,
                   a.timezone
                 )::timestamptz
               ) AS day_local
        FROM lufthansa_flight_history lfh
        JOIN routes r   ON r.id = lfh.route_id
        JOIN airports a ON a.iata_code = r.arrival_airport
        WHERE lfh.arr_airport_meteo IS NULL
          AND lfh.arrival_schedule_date = %s
        """,
        (target_date,)
    )
    for iata, day_local in cur.fetchall():
        pairs.add((iata, day_local))

    return pairs


def _prefill_cache_one_airport_one_day(cur, iata: str, day_local_ts):
    """
    Insère dans weather_hourly_cache toutes les heures de day_local (heure locale aéroport)
    à partir d'UN seul appel OWM. Retourne le nombre de lignes insérées.
    """
    ap = get_airport_from_postgres_byAirPortCode(iata)
    if not ap:
        return 0

    lat, lon, tz = ap["lat"], ap["lon"], ap["timezone"] or "UTC"

    # Un (1) appel OWM côté code métier ; la réservation quota se fait dans fetch_hourly_series()
    series = fetch_hourly_series(lat, lon, lang="fr")
    if series is None:
        # None = erreur / budget épuisé (guard interne) ; on n'arrête pas le job
        return 0

    tzinfo = ZoneInfo(tz)
    start = day_local_ts.astimezone(tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + timedelta(days=1)

    rows = []
    for p in series:
        dt_utc = p.get("_dt_utc")  # datetime aware UTC (ajouté par fetch_hourly_series)
        if not dt_utc:
            continue
        dt_loc = dt_utc.astimezone(tzinfo)
        if not (start <= dt_loc < end):
            continue
        bucket = dt_loc.replace(minute=0, second=0, microsecond=0)
        payload = {
            "datetime":    p.get("datetime"),
            "temperature": p.get("temperature"),
            "wind_speed":  p.get("wind_speed"),
            "visibility":  p.get("visibility"),
            "conditions":  p.get("conditions"),
        }
        rows.append((iata, bucket, payload))

    if not rows:
        return 0

    # INSERT ... ON CONFLICT DO NOTHING en bulk
    execute_values(
        cur,
        """
        INSERT INTO weather_hourly_cache(iata_code, hour_local, payload_json)
        VALUES %s
        ON CONFLICT (iata_code, hour_local) DO NOTHING
        """,
        rows,
        template="(%s,%s,%s::jsonb)"
    )
    return cur.rowcount or 0


def _update_departures_from_cache(cur, target_date):
    cur.execute(
        """
        WITH dep_buckets AS (
          SELECT
            lfh.id,
            r.departure_airport AS dep_iata,
            (
              make_timestamptz(
                EXTRACT(YEAR  FROM lfh.departure_schedule_date)::int,
                EXTRACT(MONTH FROM lfh.departure_schedule_date)::int,
                EXTRACT(DAY   FROM lfh.departure_schedule_date)::int,
                EXTRACT(HOUR  FROM lfh.departure_schedule_time)::int,
                0, 0,
                a.timezone
              )
            )::timestamptz AS dep_bucket_local
          FROM lufthansa_flight_history lfh
          JOIN routes   r ON r.id = lfh.route_id
          JOIN airports a ON a.iata_code = r.departure_airport
          WHERE lfh.depart_airport_meteo IS NULL
            AND lfh.departure_schedule_date = %s
        )
        UPDATE lufthansa_flight_history lfh
        SET depart_airport_meteo = c.payload_json
        FROM dep_buckets b
        JOIN weather_hourly_cache c
          ON c.iata_code = b.dep_iata
         AND c.hour_local = b.dep_bucket_local
        WHERE lfh.id = b.id
          AND lfh.depart_airport_meteo IS NULL
        """,
        (target_date,)
    )


def _update_arrivals_from_cache(cur, target_date):
    cur.execute(
        """
        WITH arr_buckets AS (
          SELECT
            lfh.id,
            r.arrival_airport AS arr_iata,
            (
              make_timestamptz(
                EXTRACT(YEAR  FROM lfh.arrival_schedule_date)::int,
                EXTRACT(MONTH FROM lfh.arrival_schedule_date)::int,
                EXTRACT(DAY   FROM lfh.arrival_schedule_date)::int,
                EXTRACT(HOUR  FROM lfh.arrival_schedule_time)::int,
                0, 0,
                a.timezone
              )
            )::timestamptz AS arr_bucket_local
          FROM lufthansa_flight_history lfh
          JOIN routes   r ON r.id = lfh.route_id
          JOIN airports a ON a.iata_code = r.arrival_airport
          WHERE lfh.arr_airport_meteo IS NULL
            AND lfh.arrival_schedule_date = %s
        )
        UPDATE lufthansa_flight_history lfh
        SET arr_airport_meteo = c.payload_json
        FROM arr_buckets b
        JOIN weather_hourly_cache c
          ON c.iata_code = b.arr_iata
         AND c.hour_local = b.arr_bucket_local
        WHERE lfh.id = b.id
          AND lfh.arr_airport_meteo IS NULL
        """,
        (target_date,)
    )


def enrich_weather_for_date(target_date_str: str, daily_budget: int = OWM_DAILY_BUDGET):
    """
    Orchestration:
      1) Calcule la liste des (IATA, day_local) à préremplir pour la date cible
      2) Borne cette liste par le budget restant réel en DB (owm_budget_remaining)
      3) Pour chaque item:
         - Re-vérifie le budget restant (concurrence sûre)
         - Fait 1 appel OWM (réservation atomique côté fetch_hourly_series)
         - Insère en bulk les heures de la journée dans weather_hourly_cache
      4) Met à jour lufthansa_flight_history depuis le cache
    """
    target_date = datetime.fromisoformat(target_date_str).date()

    # Budget restant global (partagé par tous les process) vs budget demandé par l'utilisateur
    remaining_db = owm_budget_remaining()
    effective_budget = min(daily_budget, remaining_db)

    if effective_budget <= 0:
        print(f"[weather] Budget OWM épuisé aujourd'hui (reste={remaining_db}). Rien à faire pour {target_date_str}.")
        return

    with psycopg2.connect(**PG_CONN_INFO) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            pairs = _pairs_to_prefill_for_date(cur, target_date)

            # Ordonner pour reproductibilité (pas obligatoire)
            pairs_list = sorted(list(pairs), key=lambda x: (x[0], x[1]))

            # Borne “théorique” par le budget qu'on voit maintenant
            if len(pairs_list) > effective_budget:
                pairs_list = pairs_list[:effective_budget]

            processed = 0
            for iata, day_local_ts in pairs_list:
                # Recheck live (autres process peuvent consommer le quota)
                if owm_budget_remaining() <= 0:
                    print(f"[weather] Budget OWM épuisé en cours de run. Stop préremplissage (processed={processed}).")
                    break

                _ = _prefill_cache_one_airport_one_day(cur, iata, day_local_ts)
                processed += 1

            # commit des insertions cache
            conn.commit()

            # UPDATE vols depuis le cache (cette partie ne consomme pas d'appels API)
            _update_departures_from_cache(cur, target_date)
            _update_arrivals_from_cache(cur, target_date)
            conn.commit()

    print(f"[weather] Enrichissement terminé pour {target_date_str} (préremplis={processed}, budget_initial={effective_budget}).")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Enrichit la météo (weather_hourly_cache) et met à jour lufthansa_flight_history depuis le cache."
    )
    parser.add_argument(
        "--date",
        help="Date cible au format YYYY-MM-DD (ex: 2025-09-28). Si omis, utilise la date du jour.",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=OWM_DAILY_BUDGET,
        help=f"Budget quotidien d'appels OWM (défaut: {OWM_DAILY_BUDGET})."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    # Si --date n'est pas fourni, on garde exactement la logique existante: aujourd'hui
    run_date = args.date if args.date else datetime.today().date().isoformat()
    enrich_weather_for_date(target_date_str=run_date, daily_budget=args.budget)