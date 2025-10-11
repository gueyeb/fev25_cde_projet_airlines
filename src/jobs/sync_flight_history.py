# sync_flight_history.py
from src.utils.pg_functions import getImportantRoutes
from src.utils.pg_functions import insert_dataframe, date
from src.utils.utils_functions import fetch_schedules, _safe_get, _parse_sched_datetime, cached_weather
from src.utils.utils_functions import get_airport_from_postgres_byAirPortCode_cached
import pandas as pd

# === NEW: imports pour l'argument --date ===
import argparse
import datetime as _dt


def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Synchronise lufthansa_flight_history (optionnellement pour une date donnée)."
    )
    parser.add_argument(
        "--date",
        help="Date au format YYYY-MM-DD (ex: 2025-09-28). Si non fourni, utilise la date du jour.",
    )
    return parser.parse_args()


def _resolve_run_date(cli_date_str: str | None) -> str:
    """
    Renvoie une date ISO 'YYYY-MM-DD' à utiliser pour l'appel Lufthansa et les requêtes.
    - Si cli_date_str est fourni, on valide le format et on renvoie tel quel.
    - Sinon, on garde la logique actuelle (date.today().isoformat()).
    """
    if cli_date_str:
        try:
            d = _dt.date.fromisoformat(cli_date_str)
        except ValueError:
            raise SystemExit(f"❌ --date doit être au format YYYY-MM-DD (reçu: {cli_date_str})")
        return d.isoformat()
    # logique actuelle inchangée
    return date.today().isoformat()


def sync_lufthansa_flight_history(run_date: str | None = None):
    """
    Récupère les vols du jour sur les routes importantes (aller/retour),
    et insère 1 ligne par SEGMENT de vol dans lufthansa_flight_history.

    Points clés :
      - Itère Schedule[] puis Flight[] (segments).
      - Utilise les codes aéroports du segment (ex. ZRH, FRA, ...), pas seulement la route globale.
      - Météo calculée au niveau segment, timezone issue de la table airports.
      - Colonnes JSONB : depart_airport_meteo / arr_airport_meteo.
      - Déduplication locale + contrainte unique en base :
        (marketing_carrier_airline_id, marketing_carrier_flight_number, departure_schedule_date).
    """
    # === NEW: résolution de la date d'exécution (argument CLI ou logique existante) ===
    today = _resolve_run_date(run_date)

    routes = getImportantRoutes(today)  # DataFrame: id, departure_airport, arrival_airport, ...

    print(routes.shape[0], "route(s) importante(s) à traiter pour la date", today)

    all_rows = []

    for _, route in routes.iterrows():
        route_dep = route["departure_airport"]
        route_arr = route["arrival_airport"]

        # Explorer les deux sens (A: sens "normal", R: sens inverse)
        for test_dep, test_arr in [(route_dep, route_arr), (route_arr, route_dep)]:
            sens = "A" if test_dep == route_dep else "R"
            endpoint = f"/operations/schedules/{test_dep}/{test_arr}/{today}"

            try:
                data = fetch_schedules(endpoint, "ScheduleResource.Schedule")
                if not data:
                    continue

                # D'après le JSON fourni : ScheduleResource.Schedule est une LISTE
                schedules = data if isinstance(data, list) else [data]

                for sched in schedules:
                    total_journey = _safe_get(sched, "TotalJourney", "Duration")
                    segs = _safe_get(sched, "Flight")
                    if not segs:
                        continue
                    if isinstance(segs, dict):  # normaliser en liste
                        segs = [segs]

                    for seg in segs:
                        # --- Aéroports du SEGMENT (et non pas la route globale) ---
                        dep_iata_seg = _safe_get(seg, "Departure", "AirportCode")
                        arr_iata_seg = _safe_get(seg, "Arrival",   "AirportCode")

                        # --- Infos marketing / équipement au niveau segment ---
                        marketing = _safe_get(seg, "MarketingCarrier", default={}) or {}
                        equipment = _safe_get(seg, "Equipment", default={}) or {}

                        airline_id    = marketing.get("AirlineID")
                        flight_number = marketing.get("FlightNumber")
                        aircraft_code = equipment.get("AircraftCode")

                        # --- Horaires programmés du segment ---
                        dep_date, dep_time, dep_dt, arr_date, arr_time, arr_dt = _parse_sched_datetime(seg)

                        # --- Terminaux (si présents) ---
                        dep_terminal = _safe_get(seg, "Departure", "Terminal", "Name")
                        arr_terminal = _safe_get(seg, "Arrival",   "Terminal", "Name")

                        # --- Météo au niveau SEGMENT (coords + timezone via airports) ---
                        dep_info = get_airport_from_postgres_byAirPortCode_cached(dep_iata_seg) if dep_iata_seg else None
                        arr_info = get_airport_from_postgres_byAirPortCode_cached(arr_iata_seg) if arr_iata_seg else None

                        if dep_dt and dep_info:
                            dep_bucket = dep_dt.replace(minute=0, second=0, microsecond=0).isoformat()
                            departure_airport_weather = cached_weather(
                                dep_iata_seg, dep_info["lat"], dep_info["lon"], dep_bucket, dep_info.get("timezone")
                            )
                        else:
                            departure_airport_weather = None

                        if arr_dt and arr_info:
                            arr_bucket = arr_dt.replace(minute=0, second=0, microsecond=0).isoformat()
                            arrival_airport_weather = cached_weather(
                                arr_iata_seg, arr_info["lat"], arr_info["lon"], arr_bucket, arr_info.get("timezone")
                            )
                        else:
                            arrival_airport_weather = None

                        # --- Construction de la ligne à insérer ---
                        row = {
                            "total_journey_duration": total_journey,  # duplique par segment : ok
                            "route_id": route["id"],
                            "route_sens": sens,
                            "departure_schedule_date": dep_date,
                            "departure_schedule_time": dep_time,
                            "departure_terminal": dep_terminal,
                            "arrival_schedule_date": arr_date,
                            "arrival_schedule_time": arr_time,
                            "arrival_terminal": arr_terminal,
                            "marketing_carrier_airline_id": airline_id,
                            "marketing_carrier_flight_number": flight_number,
                            "equipment_aircraft_code": aircraft_code,
                            # JSONB
                            "depart_airport_meteo": departure_airport_weather,
                            "arr_airport_meteo": arrival_airport_weather,
                        }

                        # Respecter la contrainte unique en base
                        if airline_id and flight_number and dep_date:
                            all_rows.append(row)

            except Exception as e:
                print(f"❌ Erreur API pour {test_dep}->{test_arr} : {e}")

    # Insert en bloc
    if all_rows:

        df = pd.DataFrame(all_rows)

        # Déduplication soft côté client
        df.drop_duplicates(
            subset=[
                "marketing_carrier_airline_id",
                "marketing_carrier_flight_number",
                "departure_schedule_date",
            ],
            inplace=True,
        )
        insert_dataframe(df, "lufthansa_flight_history")
        print(f"✅ Insert lufthansa_flight_history : {len(df)} ligne(s)")
    else:
        print("📭 Aucun segment à insérer pour aujourd'hui.")


if __name__ == "__main__":
    args = _parse_cli_args()
    # Passe la date (ou None) à la fonction : si None, la logique actuelle s'applique.
    sync_lufthansa_flight_history(run_date=args.date)