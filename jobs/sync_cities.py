from functions.pg_functions import insert_dataframe, pd
from functions.utils_functions import fetch_paginated
from functions.utils_functions import verify_then_sync


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


if __name__ == "__main__":
    report = verify_then_sync(
        table_name="cities",
        endpoint="/mds-references/cities",
        meta_totalcount_path="CityResource.Meta.TotalCount",
        sync_func=sync_cities,
    )
    print(f"[cities] {report}")