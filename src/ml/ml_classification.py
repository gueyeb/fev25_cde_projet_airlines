import pandas as pd
import joblib
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import numpy as np

# Add parent directory to path to import project modules
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.pg_functions import engine

# --- 1. Connexion et chargement des données ---
def get_db_engine():
    """
    Utilise le moteur de connexion configuré dans src.utils.pg_functions
    """
    return engine

def load_data_from_db(engine):
    # Load data with features available at prediction time
    # Note: delay_on_departure is NOT included (data leakage)
    # total_journey_duration calculated from schedule times
    query = """
    SELECT
        EXTRACT(EPOCH FROM (
            (arrival_schedule_date + arrival_schedule_time) -
            (departure_schedule_date + departure_schedule_time)
        )) / 60.0 as total_journey_duration_min,
        EXTRACT(EPOCH FROM delay_on_arrival) as delay_on_arrival,
        EXTRACT(DOW FROM departure_schedule_date) as departure_day_of_week,
        EXTRACT(HOUR FROM departure_schedule_time) as departure_hour,
        departure_terminal,
        arrival_terminal,
        marketing_carrier_airline_id,
        equipment_aircraft_code,
        depart_airport_meteo->>'main' as departure_airport_meteo,
        arr_airport_meteo->>'main' as arrival_airport_meteo
    FROM lufthansa_flight_history
    WHERE
        delay_on_arrival IS NOT NULL
        AND departure_schedule_date IS NOT NULL
        AND departure_schedule_time IS NOT NULL
        AND arrival_schedule_date IS NOT NULL
        AND arrival_schedule_time IS NOT NULL;
    """
    df = pd.read_sql_query(query, engine)
    # Rename for consistency
    df = df.rename(columns={'total_journey_duration_min': 'total_journey_duration'})
    return df

# --- 2. Prétraitement des données pour la classification ---
def preprocess_data_for_classification(df, delay_threshold_minutes=15):
    """
    Prépare les données et crée la variable cible 'is_late'.
    Features: total_journey_duration, departure_day_of_week, departure_hour,
              terminals, airline, aircraft, weather
    NO data leakage: delay_on_departure is NOT used
    """
    # Fill missing categorical values
    df = df.fillna('unknown')

    # Create target variable 'is_late' (delay >= 15 min)
    # delay_on_arrival is in seconds from EXTRACT(EPOCH)
    df['delay_on_arrival_minutes'] = df['delay_on_arrival'] / 60.0
    df['is_late'] = (df['delay_on_arrival_minutes'] >= delay_threshold_minutes).astype(int)

    # total_journey_duration already in minutes from SQL query

    # One-hot encode categorical variables
    categorical_cols = [
        'departure_terminal',
        'arrival_terminal',
        'marketing_carrier_airline_id',
        'equipment_aircraft_code',
        'departure_airport_meteo',
        'arrival_airport_meteo'
    ]
    df = pd.get_dummies(df, columns=categorical_cols)

    # Drop target-related columns (keep only features + is_late)
    df = df.drop(['delay_on_arrival_minutes', 'delay_on_arrival'], axis=1)

    return df

# --- 3. Création et entraînement du modèle de classification ---
def train_classification_model(df):
    """
    Sépare les données et entraîne un modèle de classification.
    """
    # Définition de la variable cible (Y) et des variables explicatives (X)
    X = df.drop('is_late', axis=1)
    y = df['is_late']

    # Séparation des données en ensembles d'entraînement et de test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Entraînement du modèle
    # Un RandomForestClassifier est idéal pour ce type de problème
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Évaluation du modèle
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Précision du modèle (Accuracy) : {accuracy:.2f}")
    print("\nRapport de classification :")
    print(classification_report(y_test, y_pred))
    
    return model

def main():
    """Main function to train the classification model"""
    try:
        db_engine = get_db_engine()
        df = load_data_from_db(db_engine)

        if not df.empty:
            print(f"[INFO] Données chargées : {len(df)} enregistrements")
            df_processed = preprocess_data_for_classification(df)
            trained_model = train_classification_model(df_processed)

            # Sauvegarder le modèle
            model_path = PROJECT_ROOT / "flight-delay-predictor" / "app" / "models" / "flight_delay_classification_model.pkl"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(trained_model, model_path)
            print(f"[SUCCESS] Modèle sauvegardé : {model_path}")
            print("[SUCCESS] Modèle de machine learning (classification) entraîné avec succès.")
        else:
            print("[WARNING] Le DataFrame est vide. Aucune donnée à traiter.")

    except Exception as e:
        print(f"[ERROR] Une erreur est survenue : {e}")
        raise

if __name__ == "__main__":
    main()