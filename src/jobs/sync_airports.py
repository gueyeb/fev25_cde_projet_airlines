from src.utils.pg_functions import city_exists
from src.utils.pg_functions import insert_dataframe, pd
from src.utils.utils_functions import fetch_paginated, verify_then_sync


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
        location_type = ap.get("LocationType")
        if iata_code and name and city_code and country_code:
            rows.append({
                "iata_code": iata_code,
                "name": name,
                "city_code": city_code,
                "country_code": country_code,
                "location_type" : location_type,
                "latitude": ap.get("Position", {}).get("Coordinate", {}).get("Latitude"),
                "longitude": ap.get("Position", {}).get("Coordinate", {}).get("Longitude"),
                "timezone": ap.get("TimeZoneId"),
                "utc_offset": ap.get("UtcOffset")
            })

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["iata_code"], inplace=True)
    insert_dataframe(df, "airports")


if __name__ == "__main__":
    report = verify_then_sync(
        table_name="airports",
        endpoint="/mds-references/airports",
        meta_totalcount_path="AirportResource.Meta.TotalCount",
        sync_func=sync_airports,
    )
    print(f"[airports] {report}")