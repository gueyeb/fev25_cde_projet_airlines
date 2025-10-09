import pandas as pd
from functions.pg_functions import insert_dataframe
from functions.utils_functions import fetch_paginated, verify_then_sync

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


def lunch_sync_aircrafts():
    report = verify_then_sync(
        table_name="aircrafts",
        endpoint="/mds-references/aircraft",
        meta_totalcount_path="AircraftResource.Meta.TotalCount",
        sync_func=sync_aircrafts,
    )
    print(f"[aircrafts] {report}")

if __name__ == "__main__":
    lunch_sync_aircrafts()