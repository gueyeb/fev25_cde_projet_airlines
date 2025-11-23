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
    # Charge les mêmes données que pour la régression
    query = """
    SELECT
        EXTRACT(EPOCH FROM total_journey_duration) as total_journey_duration,
        EXTRACT(EPOCH FROM delay_on_departure) as delay_on_departure,
        EXTRACT(EPOCH FROM delay_on_arrival) as delay_on_arrival,
        EXTRACT(DOW FROM departure_schedule_date) as departure_day_of_week,
        EXTRACT(HOUR FROM departure_schedule_time) as departure_hour,
        departure_terminal,
        arrival_terminal,
        marketing_carrier_airline_id,
        equipment_aircraft_code,
        departure_airport_meteo,
        arrival_airport_meteo
    FROM lufthansa_flight_history
    WHERE
        delay_on_arrival IS NOT NULL
        AND delay_on_departure IS NOT NULL
        AND total_journey_duration IS NOT NULL;
    """
    df = pd.read_sql_query(query, engine)
    return df

# --- 2. Prétraitement des données pour la classification ---
def preprocess_data_for_classification(df, delay_threshold_minutes=15):
    """
    Prépare les données et crée la variable cible 'is_late'.
    """
    # Remplacer les valeurs manquantes
    df = df.fillna('unknown')

    # Création de la variable cible 'is_late'
    df['delay_on_arrival_minutes'] = df['delay_on_arrival'] / 60.0
    df['is_late'] = (df['delay_on_arrival_minutes'] >= delay_threshold_minutes).astype(int)

    # Convertir les durées et les retards en minutes
    df['total_journey_duration'] = df['total_journey_duration'] / 60.0
    df['delay_on_departure'] = df['delay_on_departure'] / 60.0

    # Encodage one-hot des variables catégorielles
    categorical_cols = [
        'departure_terminal',
        'arrival_terminal',
        'marketing_carrier_airline_id',
        'equipment_aircraft_code',
        'departure_airport_meteo',
        'arrival_airport_meteo'
    ]
    df = pd.get_dummies(df, columns=categorical_cols)

    # Supprimer les colonnes de retard qui ne sont pas des features
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

if __name__ == "__main__":
    try:
        db_engine = get_db_engine()
        df = load_data_from_db(db_engine)

        if not df.empty:
            print(f"[INFO] Données chargées : {len(df)} enregistrements")
            df_processed = preprocess_data_for_classification(df)
            trained_model = train_classification_model(df_processed)

            # Sauvegarder le modèle
            model_path = PROJECT_ROOT / "flight-delay-predictor" / "app" / "models" / "flight_delay_model.pkl"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(trained_model, model_path)
            print(f"[SUCCESS] Modèle sauvegardé : {model_path}")
            print("[SUCCESS] Modèle de machine learning (classification) entraîné avec succès.")
        else:
            print("[WARNING] Le DataFrame est vide. Aucune donnée à traiter.")

    except Exception as e:
        print(f"[ERROR] Une erreur est survenue : {e}")