# DST Airlines - Flight Delay Predictor

Système de prédiction de retards de vols combinant collecte de données multi-sources, architecture hybride SQL/NoSQL, et machine learning.

## 👥 Membres du groupe

- Christian AKPONA
- Babacar GUEYE
- Yacine BIBRAS
- Aurince Judicaël AKAKPO

## 📦 Structure du projet

```bash
fev25_cde_projet_airlines/
├── config/                           # Configuration centralisée
│   ├── .env                          # Variables d'environnement (API keys, DB credentials)
│   ├── .env.example                  # Template de configuration
│   └── env_loader.py                 # Chargement des variables d'env
│
├── database/                         # Couche base de données
│   └── migrations/
│       └── 1_create_tables.sql       # Schéma PostgreSQL (tables: airlines, airports, routes, etc.)
│
├── src/                              # Code source principal
│   ├── jobs/                         # Jobs de synchronisation des données
│   │   ├── sync_airlines.py          # Synchroniser les compagnies aériennes (Lufthansa API)
│   │   ├── sync_airports.py          # Synchroniser les aéroports (Lufthansa API)
│   │   ├── sync_aircrafts.py         # Synchroniser les avions (Lufthansa API)
│   │   ├── sync_countries.py         # Synchroniser les pays
│   │   ├── sync_cities.py            # Synchroniser les villes
│   │   ├── create_routes.py          # Créer les routes avec calcul de distances
│   │   ├── sync_flight_history.py    # Synchroniser l'historique des vols (BTS)
│   │   └── update_flight_history.py  # Mise à jour de l'historique
│   │
│   ├── ml/                           # Modèles de machine learning
│   └── utils/                        # Fonctions utilitaires
│       ├── pg_functions.py           # Utilitaires PostgreSQL (insert_dataframe, etc.)
│       ├── weather_functions.py      # Enrichissement météo (OpenWeatherMap)
│       └── utils_functions.py        # Fonctions génériques
│
├── flight-delay-predictor/          # Application web de prédiction
│   ├── backend/
│   │   ├── app.py                    # API FastAPI
│   │   ├── requirements.txt          # Dépendances backend
│   │   ├── models/                   # Modèles ML (PKL)
│   │   └── utils/                    # Utilitaires backend
│   ├── frontend/
│   │   ├── templates/
│   │   │   └── index.html            # Interface utilisateur
│   │   └── static/
│   │       ├── css/styles.css
│   │       └── js/script.js
│   └── notebooks/                    # Jupyter notebooks (analyse, ML)
│
├── docs/                             # Documentation et rapports
│   ├── BTS_USA/                      # Données historiques BTS
│   ├── reports/                      # Rapports du projet
│   └── assignment/                   # Description du projet
│
├── docker-compose.yml                # Services Docker (PostgreSQL + MongoDB)
├── requirements.txt                  # Dépendances Python globales
└── README.md                         # Ce fichier
```

## 🛠️ Prérequis

- **Python 3.8+** (testé avec Python 3.14.0)
- **pip** (gestionnaire de paquets Python)
- **PostgreSQL** (local, cloud, ou via Docker)
- **MongoDB** (optionnel, pour données météo et scraping)
- **Docker et docker-compose** (optionnel, pour lancer les bases de données)

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone <repository-url>
cd fev25_cde_projet_airlines
```

### 2. Installer les dépendances Python

```bash
# Dépendances globales (data pipeline)
pip install -r requirements.txt

# Dépendances backend (application web)
pip install -r flight-delay-predictor/backend/requirements.txt
```

### 3. Configuration des bases de données

**Option A : Utiliser Docker (recommandé pour développement)**

```bash
docker-compose up -d
# PostgreSQL: localhost:5438
# MongoDB: localhost:27018
```

**Option B : Utiliser une base de données externe (cloud, local)**

Aucune action nécessaire, passez à l'étape 4.

### 4. Configurer les variables d'environnement

```bash
# Copier le fichier exemple
cp config/.env.example config/.env

# Éditer config/.env avec vos credentials :
# - Clés API (Lufthansa, OpenWeatherMap)
# - Connexion PostgreSQL (Supabase, local, ou Docker)
# - Connexion MongoDB (optionnel)
```

**Exemple de configuration :**
```bash
# PostgreSQL (Supabase)
PG_HOST=your-supabase-host.supabase.com
PG_PORT=5432
PG_DB=postgres
PG_USER=postgres.xxxxx
PG_PASSWORD=your-password

# MongoDB (optionnel)
MONGO_URI=mongodb://localhost:27018
MONGO_DB=dst_airlines

# APIs
LH_CLIENT_ID=your-lufthansa-client-id
LH_CLIENT_SECRET=your-lufthansa-secret
OWM_API_KEY=your-openweathermap-key
```

### 5. Initialiser le schéma de base de données

```bash
# Exécuter le fichier SQL de migration
psql -h <PG_HOST> -p <PG_PORT> -U <PG_USER> -d <PG_DB> -f database/migrations/1_create_tables.sql

# Ou via un client PostgreSQL (DBeaver, pgAdmin, etc.)
```

## 📊 Pipeline de données (ordre d'exécution)

Exécuter les jobs dans l'ordre suivant pour peupler la base de données :

```bash
# 1. Synchroniser les données de référence depuis l'API Lufthansa
python -m src.jobs.sync_countries      # Pays
python -m src.jobs.sync_cities         # Villes
python -m src.jobs.sync_airlines       # Compagnies aériennes
python -m src.jobs.sync_airports       # Aéroports
python -m src.jobs.sync_aircrafts      # Types d'avions

# 2. Créer les routes avec calcul de distances
python -m src.jobs.create_routes

# 3. Synchroniser l'historique des vols (BTS historical data)
python -m src.jobs.sync_flight_history

# 4. Enrichir avec les données météo (optionnel)
python -m src.jobs.enrich_weather_programmed
```

## 🌐 Application Web - Flight Delay Predictor

L'application web FastAPI permet de prédire les retards de vols en temps réel.

### Lancement du serveur

```bash
cd flight-delay-predictor/backend
python app.py

# Le serveur démarre sur http://localhost:8000
```

### Endpoints API

- `GET /` - Interface utilisateur web
- `GET /api/airports` - Liste des aéroports disponibles
- `POST /api/predict` - Prédire un retard de vol
- `GET /api/health` - Vérification de l'état du système

### Exemple de requête

```bash
curl -X POST "http://localhost:8000/api/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "flight_number": "LH400",
    "airline": "Lufthansa",
    "departure_airport": "FRA",
    "arrival_airport": "JFK",
    "scheduled_departure": "2025-10-20T10:30:00"
  }'
```

## 🧠 Architecture technique

### Base de données hybride

**PostgreSQL** (données structurées et de référence) :
- `airlines`, `airports`, `countries`, `cities`, `aircrafts` - Données Lufthansa API
- `routes` - Routes de vol avec distances calculées (geopy)
- `bts_flight_history` - Historique brut des vols US (BTS Transtats)
- `lufthansa_flight_history` - Données en temps réel Lufthansa
- `historical_flights` - Table normalisée pour ML

**MongoDB** (données variables et semi-structurées) :
- Collection `weather` - Données météo avec TTL automatique
- Collection FlightRadar24 - Résultats du scraping

### Sources de données

1. **Lufthansa Developer API** - Données de référence et vols en temps réel
2. **BTS Transtats** - Historique des retards de vols aux USA (CSV)
3. **OpenWeatherMap API** - Corrélation météo/retards
4. **FlightRadar24** - Données complémentaires (scraping)

## 🔑 APIs utilisées

- **Lufthansa Developer API** - https://developer.lufthansa.com
- **OpenWeatherMap API** - https://openweathermap.org/api
- **BTS Transtats** - https://www.transtats.bts.gov (téléchargement CSV)
- **FlightRadar24** - https://www.flightradar24.com (scraping)