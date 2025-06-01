import os
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests
import time
from functions.pg_functions import insert_dataframe,city_exists
from config.env_loader import load_env

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

# Récupération paginée
def fetch_paginated(endpoint, root_key, limit=100, max_retries=3, retry_wait=10):
    results = []
    token = get_api_key()
    first_root_key = get_first_root_key(root_key)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    current_offset=0
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
            current_offset=extract_offset_from_url(next_url)+limit
            next_url = f"{BASE_URL}{endpoint}?limit={limit}&offset={current_offset}"
            continue
        elif resp.status_code != 200:
            print(f"❌ Erreur HTTP {resp.status_code} : {resp.text}")
            break

        data = resp.json()

        # Extraction des données par root_key
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

        # Suivre les liens de pagination
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

    print(f"✅ Récupération terminée : {len(results)} éléments totaux.")
    return results


def sync_countries():
    raw = fetch_paginated("/mds-references/countries", "CountryResource.Countries.Country")

    rows = []
    for c in raw:
        country_code = c.get("CountryCode")
        names = c.get("Names", {}).get("Name", [])
        name = None

        if isinstance(names, list):
            for entry in names:
                if entry.get("@LanguageCode", "").lower() == "en":
                    name = entry.get("$")
                    break
        elif isinstance(names, dict):
            name = names.get("$")

        if country_code and name:
            rows.append({"code": country_code, "name": name})

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["code"], inplace=True)
    insert_dataframe(df, "countries")

def sync_cities():
    raw = fetch_paginated("/mds-references/cities", "CityResource.Cities.City")
    rows = []

    for c in raw:
        city_code = c.get("CityCode")
        country_code = c.get("CountryCode")
        names = c.get("Names", {}).get("Name", [])
        name = None

        if isinstance(names, list):
            for entry in names:
                if entry.get("@LanguageCode", "").lower() == "en":
                    name = entry.get("$")
                    break
        elif isinstance(names, dict):
            name = names.get("$")

        if city_code and country_code and name:
            rows.append({
                "city_code": city_code,
                "name": name,
                "country_code": country_code
            })

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["city_code"], inplace=True)
    insert_dataframe(df, "cities")


def sync_airports():
    raw = fetch_paginated("/mds-references/airports", "AirportResource.Airports.Airport")
    rows = []

    for ap in raw:
        city_code = ap.get("CityCode")
        if not city_exists(city_code):
            print(f"⚠️ Ville inconnue ignorée : {city_code}")
            continue

        name = None
        name_field = ap.get("Names", {}).get("Name")
        if isinstance(name_field, list):
            for n in name_field:
                if n.get("@LanguageCode", "").lower() == "en":
                    name = n.get("$")
                    break
        elif isinstance(name_field, dict):
            name = name_field.get("$")

        iata_code = ap.get("AirportCode")
        country_code = ap.get("CountryCode")

        if iata_code and name and city_code and country_code:
            rows.append({
                "iata_code": iata_code,
                "name": name,
                "city_code": city_code,
                "country_code": country_code,
                "latitude": ap.get("Position", {}).get("Coordinate", {}).get("Latitude"),
                "longitude": ap.get("Position", {}).get("Coordinate", {}).get("Longitude"),
                "timezone": ap.get("TimeZoneId"),
                "utc_offset": ap.get("UtcOffset")
            })

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["iata_code"], inplace=True)
    insert_dataframe(df, "airports")

def sync_airlines():
    raw = fetch_paginated("/mds-references/airlines", "AirlineResource.Airlines.Airline")
    rows = []

    for a in raw:
        airline_code = a.get("AirlineID")
        airline_code_icao = a.get("AirlineID_ICAO")

        name_field = a.get("Names", {}).get("Name", {})
        airline_name = None
        if isinstance(name_field, dict):
            airline_name = name_field.get("$")

        if airline_code and airline_name:
            rows.append({
                "airline_code": airline_code,
                "airline_name": airline_name,
                "airline_code_icao": airline_code_icao
            })

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["airline_code"], inplace=True)
    insert_dataframe(df, "airlines")


def sync_aircrafts():
    raw = fetch_paginated("/mds-references/aircraft", "AircraftResource.AircraftSummaries.AircraftSummary")
    rows = []

    for ac in raw:
        aircraft_code = ac.get("AircraftCode")
        airline_equip_code = ac.get("AirlineEquipCode")

        name_field = ac.get("Names", {}).get("Name", {})
        model = None
        if isinstance(name_field, dict):
            model = name_field.get("$")

        if aircraft_code and model:
            rows.append({
                "aircraft_code": aircraft_code,
                "airline_equip_code": airline_equip_code,
                "model": model
            })

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["aircraft_code"], inplace=True)
    insert_dataframe(df, "aircrafts")


if __name__ == "__main__":
    print("🚀 Début de la synchronisation des données de référence 🚀")
     # sync_countries()
     #  sync_cities()
     # sync_airports()
     # sync_airlines()
     # sync_aircrafts()
