import pandas as pd

from config.env_loader import load_env
from functions.pg_functions import insert_dataframe

load_env()

def load_bts_csv(file_path, table_name="bts_data_history"):
    df = pd.read_csv(file_path, sep=",", encoding="ISO-8859-1")
    insert_dataframe(df, table_name)

if __name__ == "__main__":
    load_bts_csv("../documentation/BTS_USA/Airline_Delay_Cause.csv")