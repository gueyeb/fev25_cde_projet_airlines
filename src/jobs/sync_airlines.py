from src.utils.pg_functions import insert_dataframe, pd
from src.utils.utils_functions import fetch_paginated, verify_then_sync


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

if __name__ == "__main__":
    report = verify_then_sync(
        table_name="airlines",
        endpoint="/mds-references/airlines",
        meta_totalcount_path="AirlineResource.Meta.TotalCount",
        sync_func=sync_airlines,
    )
    print(f"[airlines] {report}")