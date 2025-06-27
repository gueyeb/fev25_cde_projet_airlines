import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy import text
from config.env_loader import load_env
from datetime import date
import pandas as pd

load_env()

HOST = os.getenv("PG_HOST")
PORT = int(os.getenv("PG_PORT"))
DBNAME = os.getenv("PG_DB")
USER = os.getenv("PG_USER")
PASSWORD = os.getenv("PG_PASSWORD")

# URL-encode the password to handle special characters
PASSWORD_ENCODED = quote_plus(PASSWORD)

# Connexion PostgreSQL with properly encoded password
DB_URL = f"postgresql://{USER}:{PASSWORD_ENCODED}@{HOST}:{PORT}/{DBNAME}"
engine = create_engine(DB_URL)

def insert_dataframe(df, table_name, batch_size=5000):
    if df.empty:
        print(f"Aucune donnée à insérer pour {table_name}")
        return

    total_rows = len(df)

    if total_rows <= batch_size:
        df.to_sql(table_name, engine, if_exists='append', index=False, method='multi')
        print(f"{total_rows} lignes insérées dans {table_name}")
    else:
        print(f"Insertion par lots de {batch_size} lignes dans {table_name}...")
        for start in range(0, total_rows, batch_size):
            end = start + batch_size
            df_small = df.iloc[start:end]
            df_small.to_sql(table_name, engine, if_exists='append', index=False, method='multi')
            print(f"✔️ Lignes {start+1} à {min(end, total_rows)} insérées")

        print(f"✅ {total_rows} lignes insérées au total dans {table_name}")


def city_exists(code):
    """Vérifie si une ville existe déjà dans la table cities"""
    if not code:
        return False
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM cities WHERE city_code = :code"), {"code": code})
        return result.fetchone() is not None

def build_historical_flights_from_bts():
    df = pd.read_sql("SELECT * FROM bts_data_history", engine)

    # Construction des données pour historical_flights
    flights = []

    """
        => df.iterrows()	Méthode Pandas qui retourne un générateur de paires (index, row) où :
                • index est l'index de la ligne
                • row est un objet Series représentant la ligne
        => for _, row in ...	
            La variable _ capte l'index, mais on ne s'en sert pas, donc on le nomme _ par convention
        => row	
            Est une ligne du DataFrame sous forme de dictionnaire Pandas (row["colonne"])
    """
    for _, row in df.iterrows():
        flights.append({
            "source": "BTS",
            "delay_minutes": int(row['arr_delay']) if not pd.isna(row['arr_delay']) else None,
            "is_delayed": bool(row['arr_del15']) if not pd.isna(row['arr_del15']) and row['arr_del15'] > 0 else False,
            "bts_data_history_id": row['id']
        })

    flights_df = pd.DataFrame(flights)
    insert_dataframe(flights_df, "historical_flights")


def getAirPorts():
    airports_df = pd.read_sql("SELECT iata_code FROM airports", engine)
    iata_codes = airports_df['iata_code'].tolist()
    return iata_codes