import json
from datetime import datetime, timedelta

from sqlalchemy import text

from src.utils.pg_functions import engine
from src.utils.pg_functions import getFlightsToUpdateToday, getFlightsToUpdate, get_route_airports, pd
from src.utils.utils_functions import _safe_get, cached_weather, get_airport_from_postgres_byAirPortCode_cached, fetch_paginated, \
    parse_any, to_bucket_iso


def _calculate_delay(sched_date, sched_time, real_date, real_time):
    """
    Calcule le retard en secondes entre horaire programmé et réel.
    Retourne un interval PostgreSQL compatible ou None.
    """
    if pd.isna(sched_date) or pd.isna(sched_time) or pd.isna(real_date) or pd.isna(real_time):
        return None
    try:
        sched_dt = datetime.combine(sched_date, sched_time)
        real_dt = datetime.combine(real_date, real_time)
        delta = real_dt - sched_dt
        total_seconds = int(delta.total_seconds())
        # Format PostgreSQL interval
        return f"{total_seconds} seconds"
    except Exception:
        return None


def update_lufthansa_flight_history(days: int = 7):
    """
    Met à jour les vols des N derniers jours dont actuals_refreshed = false :
      - récupère horaires réels (Lufthansa flightstatus),
      - CALCULE les retards (horaire réel - programmé),
      - recalcule la météo aux horaires RÉELS (fallback programmés),
      - UPDATE des colonnes + flag actuals_refreshed=true.
    """
    df = getFlightsToUpdate(days=days)
    if df.empty:
        print("[INFO] Aucun vol du jour à rafraîchir (déjà à jour ou aucun vol).")
        return

    for _, row in df.iterrows():
        try:
            flight_id = int(row["id"])
            airline   = row["marketing_carrier_airline_id"]
            flight_no = row["marketing_carrier_flight_number"]

            dep_sched_d = row["departure_schedule_date"]
            dep_sched_t = row["departure_schedule_time"]
            arr_sched_d = row["arrival_schedule_date"]
            arr_sched_t = row["arrival_schedule_time"]

            # Date pour l’endpoint flightstatus
            if pd.isna(dep_sched_d):
                if pd.isna(arr_sched_d):
                    print(f"[SKIP] Skip vol id={flight_id} (pas de date planifiée)")
                    continue
                date_str = arr_sched_d.strftime("%Y-%m-%d")
            else:
                date_str = dep_sched_d.strftime("%Y-%m-%d")

            endpoint = f"/operations/flightstatus/{airline}{flight_no}/{date_str}"
            data = fetch_paginated(endpoint, "FlightStatusResource.Flights.Flight")
            if not data:
                print(f"[WARNING] Pas de flightstatus pour {airline}{flight_no} {date_str}")
                continue

            flights = data if isinstance(data, list) else [data]
            f = flights[0]

            # Horaires réels (fallback programmés) via helpers globaux
            dep_time_real_iso = (
                    _safe_get(f, "Departure", "ActualTimeLocal", "DateTime")
                    or _safe_get(f, "Departure", "ActualTimeUTC",   "DateTime")
            )
            arr_time_real_iso = (
                    _safe_get(f, "Arrival",   "ActualTimeLocal", "DateTime")
                    or _safe_get(f, "Arrival", "ActualTimeUTC",   "DateTime")
            )

            dep_real_d, dep_real_t, dep_dt = parse_any(dep_time_real_iso, dep_sched_d, dep_sched_t)
            arr_real_d, arr_real_t, arr_dt = parse_any(arr_time_real_iso, arr_sched_d, arr_sched_t)

            dep_terminal = _safe_get(f, "Departure", "Terminal", "Name") or row.get("departure_terminal")
            arr_terminal = _safe_get(f, "Arrival",   "Terminal", "Name") or row.get("arrival_terminal")

            # Calcul des retards depuis horaires réels vs programmés
            # (l'API ne fournit pas toujours le champ Delay)
            delay_dep = _calculate_delay(dep_sched_d, dep_sched_t, dep_real_d, dep_real_t)
            delay_arr = _calculate_delay(arr_sched_d, arr_sched_t, arr_real_d, arr_real_t)

            # Aéroports et TZ
            dep_iata, arr_iata = get_route_airports(int(row["route_id"])) if pd.notna(row["route_id"]) else (None, None)
            dep_info = get_airport_from_postgres_byAirPortCode_cached(dep_iata) if dep_iata else None
            arr_info = get_airport_from_postgres_byAirPortCode_cached(arr_iata) if arr_iata else None

            # Buckets horaires (1h par défaut ; passer hours=3 si tu veux coller au pas 3h d’OWM)
            dep_meteo = None
            if dep_dt and dep_info:
                dep_bucket_iso = to_bucket_iso(dep_dt, hours=1)
                dep_meteo = cached_weather(
                    dep_iata, dep_info["lat"], dep_info["lon"], dep_bucket_iso, dep_info.get("timezone")
                )

            arr_meteo = None
            if arr_dt and arr_info:
                arr_bucket_iso = to_bucket_iso(arr_dt, hours=1)
                arr_meteo = cached_weather(
                    arr_iata, arr_info["lat"], arr_info["lon"], arr_bucket_iso, arr_info.get("timezone")
                )

            # UPDATE + flag actuals_refreshed
            update_stmt = text("""
                UPDATE lufthansa_flight_history
                SET
                    real_departure_schedule_date = :dep_date,
                    real_departure_schedule_time = :dep_time,
                    real_arrival_schedule_date   = :arr_date,
                    real_arrival_schedule_time   = :arr_time,
                    departure_terminal           = :dep_terminal,
                    arrival_terminal             = :arr_terminal,
                    delay_on_departure           = :delay_dep,
                    delay_on_arrival             = :delay_arr,
                    depart_airport_meteo         = COALESCE(CAST(:dep_meteo AS jsonb), depart_airport_meteo),
                    arr_airport_meteo            = COALESCE(CAST(:arr_meteo AS jsonb), arr_airport_meteo),
                    actuals_refreshed            = true,
                    actuals_refreshed_at         = now()
                WHERE id = :flight_id
                  AND actuals_refreshed = false
            """)

            params = {
                "dep_date": dep_real_d,
                "dep_time": dep_real_t,
                "arr_date": arr_real_d,
                "arr_time": arr_real_t,
                "dep_terminal": dep_terminal,
                "arr_terminal": arr_terminal,
                "delay_dep": delay_dep,
                "delay_arr": delay_arr,
                "dep_meteo": json.dumps(dep_meteo) if dep_meteo is not None else None,
                "arr_meteo": json.dumps(arr_meteo) if arr_meteo is not None else None,
                "flight_id": flight_id
            }

            with engine.begin() as connection:
                res = connection.execute(update_stmt, params)
                if res.rowcount == 0:
                    print(f"[INFO] Vol {airline}{flight_no} déjà rafraîchi ou non éligible.")
                else:
                    print(f"[SUCCESS] Vol {airline}{flight_no} mis à jour (réels + météo) et flaggé.")

        except Exception as e:
            print(f"[ERROR] Erreur enrichissement {row.get('marketing_carrier_airline_id')}{row.get('marketing_carrier_flight_number')} : {e}")
