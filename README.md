# DST Airlines

Projet de collecte, enrichissement et prédiction de retards de vols basé sur des données ouvertes et des API.

## 👥 Membres du groupe

- AKPONA Christian
- BABACAR Gueye
- Yacine
- Aurince

## 📦 Structure du projet

```
dst-airlines/
├── config/.env.example
├── database/
│   ├── create_tables.sql
│   ├── insert_lufthansa.py
│   └── data_sources.xlsx
├── documentation/
│   ├── uml_model.pdf
│   └── api_endpoints.xlsx
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

## 🚀 Lancement rapide

1. Cloner le projet
2. Copier `.env.example` en `.env` et configurer vos clés API
3. Lancer les bases de données :
```bash
docker-compose up -d
```
4. Exécuter les scripts d’insertion :
```bash
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