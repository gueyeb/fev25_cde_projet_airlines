import pandas as pd
from geopy.distance import geodesic
from tqdm import tqdm

from functions.pg_functions import getAirPorts
from functions.pg_functions import insert_dataframe

airports_df = getAirPorts()
def create_routes(airports_df, batch_size=10000):
    routes = []
    airports_list = list(airports_df.itertuples(index=False))

    total = (len(airports_list) * (len(airports_list) - 1)) // 2
    with tqdm(total=total, desc="Génération des routes") as pbar:
        for i in range(len(airports_list)):
            a1 = airports_list[i]
            for j in range(i + 1, len(airports_list)):
                a2 = airports_list[j]
                if a1.iata_code != a2.iata_code:
                    dist = geodesic((a1.latitude, a1.longitude), (a2.latitude, a2.longitude)).km
                    routes.append({
                        'departure_airport': a1.iata_code,
                        'arrival_airport': a2.iata_code,
                        'distance': int(round(dist))
                    })

                    # Insertion par lot
                    if len(routes) >= batch_size:
                        routes_df = pd.DataFrame(routes)
                        insert_dataframe(routes_df, 'routes')
                        routes.clear()  # vider la liste après insertion

                pbar.update(1)

    # Insertion finale du reliquat
    if routes:
        routes_df = pd.DataFrame(routes)
        insert_dataframe(routes_df, 'routes')
