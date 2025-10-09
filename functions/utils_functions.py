import time
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs
from typing import Callable, Optional

from functions.weather_functions import *
from functions.pg_functions import table_count

load_env()

# Configuration API Lufthansa OAuth2
BASE_URL = os.getenv("LUFTHANSA_BASE_URL")
AUTH_URL = f"{BASE_URL}/oauth/token"
CLIENT_ID = os.getenv("LH_CLIENT_ID")
CLIENT_SECRET = os.getenv("LH_CLIENT_SECRET")

def get_first_root_key(full_key: str) -> str:
    return full_key.split('.')[0]

# Fonction pour récupérer le token d'accès
def get_api_key():
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(AUTH_URL, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]

def fetch_paginated(endpoint, root_key, limit=20, max_retries=3, retry_wait=10, MAX_CONSECUTIVE_404_ERROR_RETRY = 1):

    results = []
    token = get_api_key()
    first_root_key = get_first_root_key(root_key)

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    current_offset = 0

    next_url = f"{BASE_URL}{endpoint}?limit={limit}&offset={current_offset}"

    while next_url:
        print(f"🔄 Requête : {next_url}")
        retries = 0
        while retries <= max_retries:
            resp = requests.get(next_url, headers=headers)
            if resp.status_code == 429:
                print(f"⏳ Trop de requêtes (429), attente {retry_wait}s...")
                time.sleep(retry_wait)
                retries += 1
            else:
                break

        if resp.status_code == 404:
            print(f"⚠️ Page ignorée (404 Not Found) : {next_url}")
            current_offset = extract_offset_from_url(next_url) + limit
            next_url = f"{BASE_URL}{endpoint}?limit={limit}&offset={current_offset}"
            MAX_CONSECUTIVE_404_ERROR_RETRY -= 1
            if MAX_CONSECUTIVE_404_ERROR_RETRY == 0:
                print("🛑 Trop de 404 consécutifs, arrêt de la pagination.")
                break
            else:
                continue
        elif resp.status_code != 200:
            print(f"❌ Erreur HTTP {resp.status_code} : {resp.text}")
            break

        MAX_CONSECUTIVE_404_ERROR_RETRY = 2

        try:
            data = resp.json()
        except ValueError:
            print(f"⚠️ Réponse non-JSON reçue sur : {next_url}")
            break

        # Extraction des données
        batch = data
        for key in root_key.split('.'):
            batch = batch.get(key, {})
        if isinstance(batch, dict):
            batch = list(batch.values())
        if not batch:
            print("⚠️ Aucune donnée trouvée à ce niveau.")
            break

        results.extend(batch)
        print(f"📦 {len(batch)} éléments ajoutés — total : {len(results)}")

        # Suivre les liens de pagination (uniquement si encore autorisé)
        if MAX_CONSECUTIVE_404_ERROR_RETRY > 0:
            next_url = None
            try:
                links = data.get(first_root_key, {}).get("Meta", {}).get("Link", [])
                for link in links:
                    if link.get("@Rel") == "next":
                        next_url = link.get("@Href")
                        break
            except Exception as e:
                print(f"⚠️ Erreur de parsing Meta.Link : {e}")
                break
        else:
            break

    print(f"✅ Récupération terminée : {len(results)} éléments totaux.")
    return results

def extract_offset_from_url(url):
    """
    Extrait la valeur du paramètre offset depuis une URL.
    Ex : "https://.../airports?limit=100&offset=6800" → 6800
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    offset_values = query_params.get("offset")
    if offset_values:
        return int(offset_values[0])
    return None


# Fonction pour récupérer le token d'accès
def get_api_key():
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(AUTH_URL, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]


def parse_any(iso_str, sched_date, sched_time):
    """
    Essaie d'abord de parser un datetime ISO (ex: '2025-09-28T14:35').
    Sinon, reconstruit un datetime local à partir de (sched_date, sched_time).
    Retourne (date, time, datetime) ou (None, None, None).
    Dépend de split_iso(iso_str) -> (date, time, datetime|None).
    """
    if iso_str:
        d, t, dt = split_iso(iso_str)   # split_iso doit être défini globalement (comme dans tes helpers)
        if dt:
            return d, t, dt

    if sched_date is not None and sched_time is not None:
        try:
            # sched_time peut être un time ou une string ; str() est tolérant
            dt = datetime.fromisoformat(f"{sched_date}T{sched_time}")
            return sched_date, sched_time, dt
        except Exception:
            pass

    return None, None, None


def to_bucket_iso(dt_obj, hours=1):
    """
    Ramène un datetime sur un 'bucket' horaire (par défaut 1h).
      - hours=1  -> 14:00, 15:00, 16:00, ...
      - hours=3  -> 12:00, 15:00, 18:00, ...
    Retourne une string ISO locale (ou None si dt_obj est None).
    """
    if dt_obj is None:
        return None

    dt = dt_obj.replace(minute=0, second=0, microsecond=0)

    if hours and hours > 1:
        # quantifie l’heure au multiple inférieur de `hours`
        dt = dt.replace(hour=(dt.hour // hours) * hours)

    return dt.isoformat()


def _extract_by_path(obj: Any, path: Optional[str]) -> Any:
    if not path:
        return obj
    cur = obj
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur

def fetch_schedules(endpoint: str, root_key: Optional[str], limit=100, offset=0) -> Any:
    """
    Une seule requête, pas de pagination. Retourne les 100 premiers éléments.
    - endpoint: ex. f"/operations/schedules/{dep}/{arr}/{date_iso}"
    - root_key: ex. "ScheduleResource.Schedule"
    """

    # 1er jet de token
    token = get_api_key()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    url = f"{BASE_URL}{endpoint}?limit={limit}&offset={offset}"

    print(url)

    try:
        resp = requests.get(url, headers=headers, timeout=25)

        # Si expiré: on redemande un token et on retente UNE fois
        if resp.status_code == 401:
            token = get_api_key()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.get(url, headers=headers, timeout=25)

        if resp.status_code != 200:
            print(f"[LH] HTTP {resp.status_code} on {url}")
            return None

        data = resp.json()
        extracted = _extract_by_path(data, root_key)

        # Tronquer explicitement à 100 si c’est une liste
        if isinstance(extracted, list):
            return extracted[:100]
        return extracted

    except Exception as e:
        print(f"[LH] fetch_schedules error on {url}: {e}")
        return None


def _safe_get(d, *path, default=None):
    """Accès dict imbriqué, sans lever d'exception si une clé manque."""
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def split_iso(iso):
    """Split un ISO datetime en (date, time, datetime). Retourne (None, None, None) si parsing impossible."""
    if not iso:
        return (None, None, None)
    try:
        dt = datetime.fromisoformat(iso)
        return (dt.date(), dt.time(), dt)
    except Exception:
        return (None, None, None)

def _parse_sched_datetime(segment):
    """
    Extrait les horaires planifiés (départ/arrivée) depuis un segment Lufthansa.
    Retourne: (dep_date, dep_time, dep_dt, arr_date, arr_time, arr_dt).
    Gère les formats:
      - Departure.ScheduledTimeLocal.DateTime / Arrival.ScheduledTimeLocal.DateTime
      - ou fallback avec Departure.Date + Departure.Time (idem Arrival)
    """
    dep_iso = _safe_get(segment, "Departure", "ScheduledTimeLocal", "DateTime")
    arr_iso = _safe_get(segment, "Arrival",   "ScheduledTimeLocal", "DateTime")

    dep_date, dep_time, dep_dt = split_iso(dep_iso)
    arr_date, arr_time, arr_dt = split_iso(arr_iso)

    if dep_dt is None:
        d = _safe_get(segment, "Departure", "Date")
        t = _safe_get(segment, "Departure", "Time")
        try:
            if d and t:
                dep_dt = datetime.fromisoformat(f"{d}T{t}")
                dep_date, dep_time = dep_dt.date(), dep_dt.time()
        except Exception:
            pass

    if arr_dt is None:
        d = _safe_get(segment, "Arrival", "Date")
        t = _safe_get(segment, "Arrival", "Time")
        try:
            if d and t:
                arr_dt = datetime.fromisoformat(f"{d}T{t}")
                arr_date, arr_time = arr_dt.date(), arr_dt.time()
        except Exception:
            pass

    return dep_date, dep_time, dep_dt, arr_date, arr_time, arr_dt



def get_total_count(endpoint: str, meta_totalcount_path: str) -> Optional[int]:
    """
    Ex: endpoint="/mds-references/cities", meta_totalcount_path="CityResource.Meta.TotalCount"
    Fait UNE requête (limit=1) et extrait le TotalCount.
    """
    url = f"{BASE_URL}{endpoint}?limit=1&offset=0"

    token = get_api_key()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    resp = requests.get(url, headers=headers, timeout=25)
    if resp.status_code == 401:
        token = get_api_key()
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(url, headers=headers, timeout=25)

    if resp.status_code != 200:
        print(f"[LH] HTTP {resp.status_code} on {url}")
        return None

    data = resp.json()
    tc = _extract_by_path(data, meta_totalcount_path)
    try:
        return int(tc) if tc is not None else None
    except Exception:
        return None



def verify_then_sync(
        *,
        table_name: str,
        endpoint: str,
        meta_totalcount_path: str,
        sync_func: Callable[[], None],  # fonction qui fait l’insert/sync
) -> dict:
    """
    Retourne un petit rapport: {"api_total": int|None, "db_count": int, "action": "skip|sync|error"}
    """
    api_total = get_total_count(endpoint, meta_totalcount_path)
    db_total = table_count(table_name)

    if api_total is None:
        return {"api_total": None, "db_count": db_total, "action": "error"}

    #if db_total >= api_total:
    if db_total >= 0:
        # Rien à faire
        return {"api_total": api_total, "db_count": db_total, "action": "skip"}

    # Il manque des enregistrements -> on lance la sync
    sync_func()
    # on peut recalculer le db_count après sync (optionnel)
    new_db_total = table_count(table_name)
    return {"api_total": api_total, "db_count": new_db_total, "action": "sync"}