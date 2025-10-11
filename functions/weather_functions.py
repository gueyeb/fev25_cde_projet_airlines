import os
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo
import json

import psycopg2
import requests

from config.env_loader import load_env

load_env()

# --- CONFIGURATION ---
OWM_BASE_URL = os.getenv("OWM_BASE_URL", "https://api.openweathermap.org/data/2.5/forecast")
OWM_EXCLUDE = os.getenv("OWM_EXCLUDE", "minutely,daily,alerts,current")  # pour OneCall
OWM_API_KEY = os.getenv("OWM_API_KEY")

PG_CONN_INFO = {
    "host": os.getenv("PG_HOST"),
    "port": int(os.getenv("PG_PORT")),
    "dbname": os.getenv("PG_DB"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD")
}


def _parse_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default

OWM_DAILY_BUDGET = _parse_int_env("OWM_DAILY_BUDGET", 1000)

def _ensure_quota_table(conn):
    with conn.cursor() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS owm_api_quota(
                date_key   date PRIMARY KEY,
                used_calls integer NOT NULL DEFAULT 0
            );
        """)

def _today_utc_date():
    return datetime.utcnow().date()

def _quota_used_today(conn) -> int:
    with conn.cursor() as c:
        c.execute("SELECT used_calls FROM owm_api_quota WHERE date_key = %s", (_today_utc_date(),))
        row = c.fetchone()
        return int(row[0]) if row else 0

def owm_budget_remaining() -> int:
    """Helper: how many calls left for today (UTC)."""
    try:
        with psycopg2.connect(**PG_CONN_INFO) as conn:
            _ensure_quota_table(conn)
            return max(0, OWM_DAILY_BUDGET - _quota_used_today(conn))
    except Exception:
        return 0  # safe default

def _reserve_quota(n: int = 1) -> bool:
    """
    Réserve n appels du quota de la journée (UTC) de façon atomique.
    Retourne True si la réservation est faite, False si le budget est épuisé.
    """
    try:
        with psycopg2.connect(**PG_CONN_INFO) as conn:
            _ensure_quota_table(conn)
            with conn.cursor() as c:
                today = _today_utc_date()
                # 1) S'assurer que la ligne existe (0 si nouvelle journée)
                c.execute("""
                    INSERT INTO owm_api_quota(date_key, used_calls)
                    VALUES (%s, 0)
                    ON CONFLICT (date_key) DO NOTHING
                """, (today,))

                # 2) Réservation atomique si le budget le permet
                c.execute("""
                    UPDATE owm_api_quota
                       SET used_calls = used_calls + %s
                     WHERE date_key = %s
                       AND used_calls + %s <= %s
                 RETURNING used_calls
                """, (n, today, n, OWM_DAILY_BUDGET))

                row = c.fetchone()
                return bool(row)  # True si la ligne a été mise à jour
    except Exception as e:
        print(f"[weather] La réservation de Quota reservation a échoué: {e}")
        return False
def _mark_quota_exhausted():
    """Marque la journée comme épuisée (used_calls = OWM_DAILY_BUDGET)."""
    try:
        with psycopg2.connect(**PG_CONN_INFO) as conn:
            _ensure_quota_table(conn)
            with conn.cursor() as c:
                today = _today_utc_date()
                c.execute("""
                    INSERT INTO owm_api_quota(date_key, used_calls)
                    VALUES (%s, %s)
                    ON CONFLICT (date_key) DO UPDATE
                        SET used_calls = EXCLUDED.used_calls
                """, (today, OWM_DAILY_BUDGET))
    except Exception as e:
        print(f"[weather] Mark quota exhausted failed: {e}")

def get_airports_from_postgres():
    with psycopg2.connect(**PG_CONN_INFO) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT iata_code, latitude, longitude
            FROM airports
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        rows = cur.fetchall()
    return [{"iata_code": r[0], "lat": r[1], "lon": r[2]} for r in rows]
def get_airport_from_postgres_byAirPortCode(iata_code: str):
    norm = _normalize_iata(iata_code)
    if not norm:
        return None

    try:
        # Contexte garantit la fermeture de la connexion/cursor
        with psycopg2.connect(**PG_CONN_INFO) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT iata_code, latitude, longitude, timezone
                    FROM airports
                    WHERE iata_code = %s
                      AND latitude IS NOT NULL
                      AND longitude IS NOT NULL
                    """,
                    (norm,)
                )
                row = cur.fetchone()
                if row:
                    iata, lat, lon, timezone = row[0], row[1], row[2], row[3]
                    # Cast propre (au cas où)
                    try:
                        lat = float(lat)
                        lon = float(lon)
                        timezone = str(timezone)
                    except Exception:
                        return None
                    return {"iata_code": iata, "lat": lat, "lon": lon, "timezone": timezone}
        return None
    except Exception as e:
        # Log minimal; tu peux remplacer par logging.warning(...)
        print(f"[weather] Lookup aeroport échoué pour {norm}: {e}")
        return None

@lru_cache(maxsize=10000)
def get_airport_from_postgres_byAirPortCode_cached(iata_code: str):
    """
    Version cachée en mémoire (durée du process) pour limiter les hits DB.
    Utilise la fonction d'accès Postgres ci-dessous.
    """
    return get_airport_from_postgres_byAirPortCode(iata_code)

# --- APPEL API OPENWEATHERMAP ---

# Clé API
# OWM_API_KEY doit déjà être défini (env ou config)

def fetch_weather_at(lat, lon, target_datetime_local, airport_tz_str=None):
    """
    Récupère la prévision météo OWM la plus proche d'un datetime local aéroport.
    Supporte automatiquement:
      - /data/2.5/forecast  (champ 'list' avec main.temp, wind.speed, weather[])
      - /onecall (2.5 ou 3.0) (champ 'hourly' avec temp, wind_speed, weather[])
    Retourne un dict normalisé:
      {
        "datetime": ISO8601 UTC,
        "temperature": float °C,
        "wind_speed": float m/s,
        "visibility": int m (0 si absent),
        "conditions": ["Rain", "Clouds", ...]
      }
    """
    try:
        if target_datetime_local is None:
            return None

        # 1) Local -> aware
        if target_datetime_local.tzinfo is None:
            tz = ZoneInfo(airport_tz_str) if airport_tz_str else timezone.utc
            target_local_aware = target_datetime_local.replace(tzinfo=tz)
        else:
            target_local_aware = target_datetime_local

        # 2) Local -> UTC (les timestamps OWM sont en UTC)
        target_utc = target_local_aware.astimezone(timezone.utc)

        # 3) Appel OWM
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OWM_API_KEY,
            "units": "metric",
            "lang": "fr",
        }

        if "onecall" in OWM_BASE_URL:
            if OWM_EXCLUDE:
                params["exclude"] = OWM_EXCLUDE

        # --- Quota guard: stop early if daily budget exhausted ---
        if not _reserve_quota(1):
            print(f"[weather] Budget OWM épuisé ({OWM_DAILY_BUDGET}/jour). Appel ignoré pour {lat},{lon} à {target_utc.isoformat()}.")
            return None

        resp = requests.get(OWM_BASE_URL, params=params, timeout=20)
        if resp.status_code == 429:
            print(f"[weather] OWM 429 Too Many Requests, on marque le quota comme épuisé. url={resp.url}")
            _mark_quota_exhausted()
            return None
        if resp.status_code != 200:
            print(f"[weather] Erreur météo (HTTP {resp.status_code}) url={resp.url} body={resp.text[:200]}")
            return None

        data = resp.json()

        # 4) Détecter le format : 'list' (forecast) vs 'hourly' (onecall)
        forecasts = None
        mode = None

        if isinstance(data.get("list"), list) and data["list"]:
            # --- Format forecast 3h: data/2.5/forecast ---
            mode = "forecast"
            forecasts = data["list"]

            def to_dt(f):  # UTC aware
                return datetime.fromtimestamp(f["dt"], tz=timezone.utc)

            def get_temp(f):
                return f["main"]["temp"]

            def get_wind_speed(f):
                return f["wind"]["speed"]

            def get_visibility(f):
                return f.get("visibility", 0)

            def get_conditions(f):
                return [w["main"] for w in f.get("weather", [])]

        elif isinstance(data.get("hourly"), list) and data["hourly"]:
            # --- Format onecall: data/3.0/onecall (ou 2.5/onecall) ---
            mode = "onecall"
            forecasts = data["hourly"]

            def to_dt(f):
                return datetime.fromtimestamp(f["dt"], tz=timezone.utc)

            def get_temp(f):
                return f["temp"]

            def get_wind_speed(f):
                return f.get("wind_speed", 0.0)

            def get_visibility(f):
                # One Call hourly ne fournit pas toujours 'visibility'
                return f.get("visibility", 0)

            def get_conditions(f):
                return [w["main"] for w in f.get("weather", [])]

        else:
            # Aucun des deux formats attendus
            print(f"[weather] Format OWM inattendu: clés disponibles={list(data.keys())[:5]}")
            return None

        # 5) Choisir la prévision dont le dt (UTC) est le plus proche de target_utc
        closest = min(forecasts, key=lambda f: abs(to_dt(f) - target_utc))

        return {
            "datetime": to_dt(closest).isoformat(),
            "temperature": get_temp(closest),
            "wind_speed": get_wind_speed(closest),
            "visibility": get_visibility(closest),
            "conditions": get_conditions(closest),
        }

    except Exception as e:
        print(f"[weather] fetch_weather_at error: {e}")
        return None


def hour_bucket_local(dt_local: datetime, tz_str: str) -> datetime:
    tz = ZoneInfo(tz_str) if tz_str else timezone.utc
    aware = dt_local.replace(tzinfo=tz) if dt_local.tzinfo is None else dt_local.astimezone(tz)
    return aware.replace(minute=0, second=0, microsecond=0)



@lru_cache(maxsize=10000)
def cached_weather(iata: str, lat: float, lon: float, hour_bucket_iso: str, airport_tz_str: str | None):
    dt_local = datetime.fromisoformat(hour_bucket_iso)  # local
    bucket = hour_bucket_local(dt_local, airport_tz_str or "UTC")

    # 1) Lire le cache DB
    with psycopg2.connect(**PG_CONN_INFO) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT payload_json
            FROM weather_hourly_cache
            WHERE iata_code = %s AND hour_local = %s
            LIMIT 1
        """, (iata, bucket))
        row = cur.fetchone()
        if row:
            return row[0]  # dict JSONB

    # 2) Manquant : appeler OWM
    data = fetch_weather_at(lat, lon, bucket, airport_tz_str=airport_tz_str)
    if data:
        # insérer dans le cache pour réutilisation
        with psycopg2.connect(**PG_CONN_INFO) as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO weather_hourly_cache(iata_code, hour_local, payload_json)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (iata, bucket, json.dumps(data)))
        return data

    return None



def _normalize_iata(code: str) -> str:
    if not code:
        return ""
    return code.strip().upper()


def fetch_hourly_series(lat: float, lon: float, *, lang: str = "fr"):
    """
    1 appel OWM -> renvoie une liste normalisée d'éléments horaires :
    [
      {
        "datetime": "<ISO8601 UTC>",
        "temperature": <float °C>,
        "wind_speed": <float m/s>,
        "visibility": <int m>,
        "conditions": ["Rain", "Clouds", ...],
        "_dt_utc": <datetime aware UTC>  # pratique pour conversion locale
      },
      ...
    ]
    Retourne [] si aucun point, ou None en cas d'erreur HTTP/format.
    """
    try:
        # Quota guard for bulk call
        if not _reserve_quota(1):
            print(f"[weather] Budget OWM épuisé ({OWM_DAILY_BUDGET}/jour). Appel bulk ignoré pour lat={lat}, lon={lon}.")
            return []

        params = {
            "lat": lat,
            "lon": lon,
            "appid": OWM_API_KEY,
            "units": "metric",
            "lang": lang,
        }
        if "onecall" in OWM_BASE_URL and OWM_EXCLUDE:
            params["exclude"] = OWM_EXCLUDE

        resp = requests.get(OWM_BASE_URL, params=params, timeout=25)
        if resp.status_code == 429:
            print(f"[weather] OWM 429 Too Many Requests (bulk).")
            _mark_quota_exhausted()
            return []
        if resp.status_code != 200:
            print(f"[weather] Erreur météo bulk (HTTP {resp.status_code}) url={resp.url} body={resp.text[:200]}")
            return []

        resp.raise_for_status()
        data = resp.json()

        out = []

        # Détecter OneCall vs Forecast
        if isinstance(data.get("hourly"), list) and data["hourly"]:
            # OneCall: hourly[]
            for h in data["hourly"]:
                dt_utc = datetime.fromtimestamp(h["dt"], tz=timezone.utc)
                payload = {
                    "datetime": dt_utc.isoformat(),
                    "temperature": h.get("temp"),
                    "wind_speed": h.get("wind_speed", 0.0),
                    "visibility": h.get("visibility", 0),
                    "conditions": [w.get("main") for w in h.get("weather", [])],
                    "_dt_utc": dt_utc,
                }
                out.append(payload)

        elif isinstance(data.get("list"), list) and data["list"]:
            # Forecast 3h: list[]
            for f in data["list"]:
                dt_utc = datetime.fromtimestamp(f["dt"], tz=timezone.utc)
                payload = {
                    "datetime": dt_utc.isoformat(),
                    "temperature": f["main"]["temp"],
                    "wind_speed": f["wind"]["speed"],
                    "visibility": f.get("visibility", 0),
                    "conditions": [w.get("main") for w in f.get("weather", [])],
                    "_dt_utc": dt_utc,
                }
                out.append(payload)
        else:
            print(f"[weather] Format OWM inattendu (bulk): keys={list(data.keys())[:6]}")
            return []

        return out

    except Exception as e:
        print(f"[weather] fetch_hourly_series error: {e}")
        return None