from src.utils.pg_functions import insert_dataframe, pd
from src.utils.utils_functions import fetch_paginated
from src.utils.utils_functions import verify_then_sync


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


if __name__ == "__main__":
    report = verify_then_sync(
        table_name="countries",
        endpoint="/mds-references/countries",
        meta_totalcount_path="CountryResource.Meta.TotalCount",
        sync_func=sync_countries,
    )
    print(f"[countries] {report}")