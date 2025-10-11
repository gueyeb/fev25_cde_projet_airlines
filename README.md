# DST Airlines

Projet de collecte, enrichissement et prédiction de retards de vols basé sur des données ouvertes et des API.

## 👥 Membres du groupe

- Christian AKPONA
- Babacar GUEYE
- Yacine BIBRAS
- Aurince Judicaël AKAKPO

## 📦 Structure du projet

``` bash
dst-airlines/
├── config/.env.example
├── database/
│   ├── 1_create_tables.sql
│   ├── insert_lufthansa.py
│   └── data_sources.xlsx
├── documentation/
│   ├── uml_model.pdf
│   └── api_endpoints.xlsx
│   └── DST Airlines.pdf
│   └── dst_airline_er_diagram.png
│   └── rapports/
│   └── BTS_USA/
│      └── Airline_Delay_Cause.csv
│      └── Download_Column_Definitions.xlsx
├── docker-compose.yml
├── ingestion/
│   └── lufthansa_to_postgresql.py
├── nosql/
│   ├── mongodb_schemas.json
│   ├── nosql_sources.xlsx
│   ├── fetch_weather_to_mongodb.py
│   └── setup_weather_ttl_index.py
├── scraping/
│   ├── flightradar_scraper_to_mongodb.py
│   └── automated_flightradar_scraper.py
└── README.md
```

## 🛠️ Prérequis

Avant de lancer le projet, assurez-vous d'avoir installé :

- **Python 3.8+**
- **pip** (gestionnaire de paquets Python)
- **Docker** et **docker-compose** (pour l'orchestration des services)
- Les dépendances Python du projet :

```bash
pip install -r requirements.txt
```

## 🚀 Lancement rapide

1. Cloner le projet
2. Copier `config/.env.example` en `config/.env` et configurer vos clés API
3. Lancer les bases de données :

```bash
docker-compose up -d
```

Alternativement, vous pouvez lancer une base postgreSQL/noSQL en local ou sur le cloud, et renseignez les informations de connexion dans le fichier `config/.env`

4. Exécuter les scripts d'insertion :

```bash
pip install -r requirements.txt

python database/insert_lufthansa_references_data.py
python nosql/fetch_weather_to_mongodb.py
```

## 🧠 Objectif

- Rassembler des données fiables de vols
- Les enrichir avec la météo
- Stocker dans PostgreSQL et MongoDB
- Préparer les données pour la prédiction de retards

## 🔗 APIs utilisées

- Lufthansa Developer API
- OpenWeatherMap
- BTS Transtats (CSV)
- FlightRadar24 (scraping)