# DST Airlines - Flight Delay Predictor

Système de prédiction de retards de vols combinant collecte de données multi-sources, architecture hybride SQL/NoSQL, orchestration de workflows avec Prefect, et machine learning.

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
│   ├── migrations/                   # Scripts SQL de migration
│   │   ├── 1_create_tables.sql      # Schéma PostgreSQL complet
│   │   ├── 2_aircrafts.sql          # Données initiales - avions
│   │   ├── 3_airlines.sql           # Données initiales - compagnies
│   │   ├── 4_airports.sql           # Données initiales - aéroports
│   │   ├── 5_countries.sql          # Données initiales - pays
│   │   └── 6_cities.sql             # Données initiales - villes
│   └── schema_init.sql              # Script d'initialisation complet
│
├── prefect_flows/                    # Workflows Prefect (orchestration)
│   ├── reference_data_flow.py        # Flow de synchronisation des données de référence
│   ├── flight_data_flow.py           # Flow de collecte des vols quotidiens
│   ├── update_actuals_flow.py        # Flow de mise à jour des statuts de vols
│   ├── ml_training_flow.py           # Flow d'entraînement ML
│   └── deploy_flows.py               # Script de déploiement des flows
│
├── src/                              # Code source principal
│   ├── jobs/                         # Jobs de synchronisation des données
│   │   ├── sync_airlines.py          # Synchroniser les compagnies aériennes (Lufthansa API)
│   │   ├── sync_airports.py          # Synchroniser les aéroports (Lufthansa API)
│   │   ├── sync_aircrafts.py         # Synchroniser les avions (Lufthansa API)
│   │   ├── sync_countries.py         # Synchroniser les pays
│   │   ├── sync_cities.py            # Synchroniser les villes
│   │   ├── create_routes.py          # Créer les routes avec calcul de distances
│   │   └── update_flight_actuals.py  # Mise à jour des statuts de vols en temps réel
│   │
│   ├── ml/                           # Modèles de machine learning
│   │   ├── ml_classification.py      # Modèle de classification (retard Oui/Non)
│   │   └── ml_regression.py          # Modèle de régression (durée du retard)
│   │
│   └── utils/                        # Fonctions utilitaires
│       ├── pg_functions.py           # Utilitaires PostgreSQL (insert_dataframe, etc.)
│       ├── weather_functions.py      # Enrichissement météo (OpenWeatherMap)
│       └── utils_functions.py        # Fonctions génériques
│
├── flight-delay-predictor/          # Application web de prédiction
│   ├── app/                          # Application FastAPI
│   │   ├── app.py                    # Point d'entrée FastAPI
│   │   ├── requirements.txt          # Dépendances de l'application
│   │   ├── models/                   # Modèles ML (PKL)
│   │   │   ├── flight_delay_classification_model.pkl
│   │   │   └── flight_delay_regression_model.pkl
│   │   ├── utils/                    # Utilitaires backend
│   │   ├── templates/
│   │   │   └── index.html            # Interface utilisateur
│   │   └── static/
│   │       ├── css/styles.css
│   │       └── js/script.js
│   └── Dockerfile                    # Image Docker de l'application
│
├── supabase/                         # Instance Supabase auto-hébergée
│   ├── docker-compose.yml            # Services Supabase (PostgreSQL, Auth, REST, etc.)
│   └── .env                          # Configuration Supabase
│
├── docker-compose.supabase.yml       # Déploiement production (VPS + Supabase)
├── docker-compose.local.yml          # Déploiement local (PostgreSQL inclus)
├── deploy-dst-airlines.sh            # Script de gestion des services
├── init_database.sh                  # Script d'initialisation de la base
├── test_flow.sh                      # Script de test interactif des flows
├── requirements.txt                  # Dépendances Python globales
└── README.md                         # Ce fichier
```

## 🛠️ Prérequis

- **Python 3.8+** (testé avec Python 3.11)
- **Docker et docker-compose** (pour Supabase et Prefect)
- **Accès Internet** (pour les APIs Lufthansa et OpenWeatherMap)

## 🚀 Installation et déploiement

### 1. Cloner le projet

```bash
git clone <repository-url>
cd fev25_cde_projet_airlines
```

### 2. Configuration des variables d'environnement

```bash
# Copier le fichier exemple
cp config/.env.example config/.env

# Éditer config/.env avec vos credentials
nano config/.env
```

**Variables importantes à configurer :**

```bash
# PostgreSQL (Supabase auto-hébergé)
PG_HOST=dst-airlines-supabase-db
PG_PORT=5433
PG_DB=postgres
PG_USER=postgres
PG_PASSWORD=votre_mot_de_passe_securise

# APIs externes
LH_CLIENT_ID=votre_client_id_lufthansa
LH_CLIENT_SECRET=votre_secret_lufthansa
OWM_API_KEY=votre_cle_openweathermap

# MongoDB (optionnel)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=dst_airlines
```

### 3. Démarrage des services

Le projet supporte deux modes de déploiement :

#### Mode Production (VPS avec Supabase externe)

```bash
# Démarrer tous les services
./deploy-dst-airlines.sh start

# Vérifier le statut
./deploy-dst-airlines.sh status

# Voir les logs
./deploy-dst-airlines.sh logs

# Arrêter / Redémarrer
./deploy-dst-airlines.sh stop
./deploy-dst-airlines.sh restart
```

#### Mode Local (laptop avec PostgreSQL intégré)

Pour tester sur un laptop sans dépendance externe :

```bash
# Démarrer les services locaux (inclut PostgreSQL)
./deploy-dst-airlines.sh start-local

# Autres commandes locales
./deploy-dst-airlines.sh status-local
./deploy-dst-airlines.sh logs-local
./deploy-dst-airlines.sh stop-local
./deploy-dst-airlines.sh rebuild-local
./deploy-dst-airlines.sh clean-local
```

**Configuration DB personnalisée** (optionnel) :

```bash
# Utiliser un serveur PostgreSQL externe
export PG_HOST=mon-serveur-postgres.com
export PG_PORT=5432
export PG_USER=postgres
export PG_PASSWORD=mon_mot_de_passe
export PG_DB=postgres
./deploy-dst-airlines.sh start-local
```

Par défaut : `postgres:localdev@localhost:5432/postgres`

### 4. Initialisation de la base de données

```bash
# Exécuter le script d'initialisation
./init_database.sh
```

Ce script crée automatiquement :
- 11 tables PostgreSQL (countries, cities, airlines, airports, aircrafts, routes, etc.)
- Toutes les séquences nécessaires
- Les index pour optimiser les performances
- Les contraintes de clés étrangères

### 5. Déploiement des workflows Prefect

```bash
# Déployer tous les flows avec leurs planifications
./deploy-dst-airlines.sh deploy-flows
```

Les flows seront automatiquement exécutés selon leur planification.

## 🔄 Workflows Prefect (Orchestration automatisée)

Le projet utilise **Prefect 3** pour orchestrer automatiquement tous les pipelines de données et ML.

### Accès à l'interface Prefect

| Mode | URL |
|------|-----|
| Local | http://localhost:4201 |
| Production | https://dst-prefect.srv869578.hstgr.cloud |

### Flows disponibles

| Flow | Description | Planification | Fréquence |
|------|-------------|---------------|-----------|
| **reference_data_sync_flow** | Synchronisation des données de référence + marquage des routes importantes | Samedi 1h00 UTC | Hebdomadaire |
| **daily_flight_data_flow** | Collecte des plannings de vols sur les routes importantes | Quotidien 2h00 UTC | Quotidienne |
| **update_flight_actuals_flow** | Mise à jour des statuts de vols en temps réel | 6h, 10h, 14h, 18h, 22h UTC | 5 fois par jour |
| **ml_training_flow** | Entraînement des modèles de machine learning | Dimanche 3h00 UTC | Hebdomadaire |

### Exécution manuelle des flows

#### Méthode 1 : Script interactif (recommandé)

```bash
./test_flow.sh

# Menu interactif :
# 1. Reference Data Flow - Synchroniser les données de référence
# 2. Flight Data Flow - Synchroniser les plannings de vols
# 3. Update Actuals Flow - Mettre à jour les statuts de vols
# 4. ML Training Flow - Entraîner les modèles ML
```

#### Méthode 2 : Ligne de commande Python

```bash
# Flow 1 : Données de référence
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from reference_data_flow import reference_data_sync_flow
reference_data_sync_flow(skip_routes=False)
"

# Flow 2 : Données de vols quotidiennes
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from flight_data_flow import daily_flight_data_flow
daily_flight_data_flow()
"

# Flow 3 : Mise à jour des statuts de vols
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from update_actuals_flow import update_flight_actuals_flow
update_flight_actuals_flow()
"

# Flow 4 : Entraînement ML (classification + régression)
docker exec dst-airlines-prefect-agent python -c "
import sys
sys.path.insert(0, '/app/prefect_flows')
from ml_training_flow import ml_training_flow
ml_training_flow(train_both_models=True)
"
```

#### Méthode 3 : Via l'interface Prefect UI

1. Accéder à l'interface : https://dst-prefect.srv869578.hstgr.cloud
2. Cliquer sur **"Deployments"** dans le menu de gauche
3. Sélectionner un deployment (ex: "weekly-reference-sync")
4. Cliquer sur le bouton **"Run"** en haut à droite
5. Ajouter des paramètres si nécessaire
6. Cliquer sur **"Run"** pour exécuter
7. Suivre l'exécution dans **"Flow Runs"**

#### Méthode 4 : Via la CLI Prefect

```bash
# Lister tous les deployments
docker exec dst-airlines-prefect-agent prefect deployment ls

# Exécuter un deployment spécifique
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'reference_data_sync_flow/weekly-reference-sync'

# Exécuter avec des paramètres
docker exec dst-airlines-prefect-agent \
  prefect deployment run 'reference_data_sync_flow/weekly-reference-sync' \
  --param skip_routes=true

# Vérifier les exécutions
docker exec dst-airlines-prefect-agent prefect flow-run ls --limit 10
```

### Surveillance et logs

```bash
# Suivre les logs en temps réel
docker logs -f dst-airlines-prefect-agent

# Dernières 100 lignes
docker logs --tail 100 dst-airlines-prefect-agent

# Avec timestamps
docker logs -f --timestamps dst-airlines-prefect-agent

# Logs du serveur Prefect
./deploy-dst-airlines.sh logs-prefect
```

### Routes importantes

Pour limiter les appels API Lufthansa, seules les routes entre **aéroports majeurs** sont synchronisées quotidiennement. Les routes "importantes" sont marquées automatiquement lors du `reference_data_sync_flow`.

**36 hubs couverts :**

| Région | Aéroports |
|--------|-----------|
| Lufthansa Group | FRA, MUC, ZRH, VIE, BRU |
| Europe | LHR, CDG, AMS, MAD, BCN, FCO, IST, DUB, CPH, OSL, ARN |
| USA | JFK, LAX, ORD, ATL, DFW, MIA, SFO, BOS, IAD, EWR |
| Asie | NRT, HND, PEK, PVG, HKG, SIN, ICN, BKK, DXB, DOH |

**Gestion manuelle :**

```bash
# Voir les statistiques
python -m src.jobs.mark_important_routes --stats

# Prévisualiser (sans modifier)
python -m src.jobs.mark_important_routes --dry-run

# Marquer les routes importantes
python -m src.jobs.mark_important_routes

# Réinitialiser (tout remettre à non-important)
python -m src.jobs.mark_important_routes --reset
```

## 🤖 Machine Learning - Modèles de prédiction

Le système entraîne automatiquement deux modèles de prédiction :

### Modèle de Classification

**Objectif** : Prédire si un vol sera en retard (>15 minutes)

- **Algorithme** : RandomForestClassifier (100 arbres)
- **Sortie** : Binaire (Oui/Non)
- **Fichier** : `flight_delay_classification_model.pkl`
- **Métriques** : Accuracy ~77%, Precision, Recall, F1-Score

**Features utilisées** :
- Durée totale du voyage
- Retard au départ
- Jour de la semaine
- Heure de départ
- Terminal de départ/arrivée
- Compagnie aérienne
- Type d'avion
- Météo aux aéroports de départ/arrivée

### Modèle de Régression

**Objectif** : Prédire la durée du retard en minutes

- **Algorithme** : RandomForestRegressor (100 arbres)
- **Sortie** : Durée en minutes
- **Fichier** : `flight_delay_regression_model.pkl`
- **Métriques** : RMSE ~9 min, R² Score ~0.76

## 📈 Monitoring & Observabilité

Le projet inclut une stack complète d'observabilité pour surveiller la santé de l'application et de l'infrastructure en temps réel.

### Services inclus

| Service | Rôle | Port | URL |
|---------|------|------|-----|
| **Grafana** | Visualisation & Dashboards | 3000 | http://localhost:3000 (admin/admin) |
| **Prometheus** | Collecte de métriques | 9090 | http://localhost:9090 |
| **Loki** | Agrégation de logs | 3100 | - |
| **Promtail** | Agent de collecte de logs | - | - |
| **cAdvisor** | Métriques Docker (CPU/RAM) | 8080 | http://localhost:8080 |

### Dashboards pré-configurés

Un dashboard "DST Airlines Overview" est provisionné automatiquement au démarrage. Il permet de visualiser :
- **Trafic API** : Requêtes par seconde, codes de statut (200, 500, etc.)
- **Performance** : Latence moyenne des prédictions
- **Infrastructure** : Consommation CPU et RAM des conteneurs (Backend, Postgres, Prefect)

## 🌐 Application Web - Flight Delay Predictor

L'application web FastAPI permet de prédire les retards de vols en temps réel.

L'API Lufthansa FlightStatus ne fournit pas directement le champ `Delay`. Les retards sont **calculés automatiquement** :

```
delay = horaire_réel - horaire_programmé
```

**Important** : L'API ne conserve les données FlightStatus que ~7-10 jours. Pour accumuler des données historiques, exécuter quotidiennement :

```bash
# Enrichir les vols des 7 derniers jours avec retards réels
python -c "from src.jobs.update_flight_history import update_lufthansa_flight_history; update_lufthansa_flight_history(days=7)"
```

### Entraînement manuel des modèles

```bash
# Classification uniquement
docker exec dst-airlines-prefect-agent python -m src.ml.ml_classification

# Régression uniquement
docker exec dst-airlines-prefect-agent python -m src.ml.ml_regression

# Les deux modèles via Prefect
./test_flow.sh
# Choisir option 4 : ML Training Flow
```

### Prérequis pour l'entraînement

- Données Lufthansa enrichies avec `actuals_refreshed = true`
- Ou données BTS dans `bts_flight_history`
- Données météo enrichies (optionnel mais recommandé)

### Utilisation des modèles

Les modèles sont automatiquement chargés par l'application FastAPI au démarrage. Aucune action manuelle n'est nécessaire après l'entraînement.

## 🌐 Application Web - Flight Delay Predictor

L'application web FastAPI permet de prédire les retards de vols en temps réel.

### Accès à l'application

| Mode | URL |
|------|-----|
| Local | http://localhost:8001 |
| Production | https://dst-airlines.srv869578.hstgr.cloud |

### Endpoints API

**Interface utilisateur**
- `GET /` - Interface web complète

**Prédiction de retards**
- `GET /api/airports` - Liste des aéroports disponibles
- `POST /api/predict` - Prédire un retard de vol

**Consultation des données de référence** (avec pagination)
- `GET /api/data/countries?limit=100&offset=0` - Pays
- `GET /api/data/cities?limit=100&offset=0` - Villes
- `GET /api/data/airlines?limit=100&offset=0` - Compagnies aériennes
- `GET /api/data/airports?limit=100&offset=0` - Aéroports
- `GET /api/data/aircrafts?limit=100&offset=0` - Types d'avions
- `GET /api/data/routes?limit=100&offset=0` - Routes de vol

**Système**
- `GET /api/health` - État du système

### Exemples de requêtes

**Prédire un retard de vol :**

```bash
curl -X POST "http://localhost:8001/api/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "flight_number": "LH400",
    "airline": "Lufthansa",
    "departure_airport": "FRA",
    "arrival_airport": "JFK",
    "scheduled_departure": "2025-10-20T10:30:00"
  }'
```

**Consulter les compagnies aériennes :**

```bash
curl "http://localhost:8001/api/data/airlines?limit=10"
```

**Vérifier l'état du système :**

```bash
curl "http://localhost:8001/api/health"
```

## 🧠 Architecture technique

### Services Docker

Le projet déploie les services suivants :

1.  **Supabase PostgreSQL** : Base de données principale (port 5433)
2.  **Supabase Services** : Auth, REST API, Realtime, Storage, Studio
3.  **Prefect Server** : Serveur d'orchestration (port 4201)
4.  **Prefect Worker** : Exécution des workflows
5.  **FastAPI Web App** : Application de prédiction (port 8001)
6.  **Monitoring Stack** : Prometheus, Grafana, Loki, Promtail, cAdvisor

### Base de données PostgreSQL

**Tables principales** :

| Table | Description | Lignes |
|-------|-------------|--------|
| `countries` | Pays | ~100 |
| `cities` | Villes | ~3000 |
| `airlines` | Compagnies aériennes | ~500 |
| `airports` | Aéroports | ~8000 |
| `aircrafts` | Types d'avions | ~300 |
| `routes` | Routes de vol avec distances | ~50000 |
| `lufthansa_flight_history` | Historique des vols Lufthansa | Variable |
| `bts_flight_history` | Historique BTS (USA) | ~100000 |
| `historical_flights` | Table normalisée pour ML | Variable |
| `weather_hourly_cache` | Cache météo horaire | Variable |
| `owm_api_quota` | Suivi des quotas API OpenWeatherMap | ~365 |

### Sources de données

1. **Lufthansa Developer API** - Données de référence et vols en temps réel
   - URL : https://developer.lufthansa.com
   - Fréquence : Temps réel / Quotidien
   - Limites : Rate limiting (requêtes par seconde)

2. **OpenWeatherMap API** - Données météo
   - URL : https://openweathermap.org/api
   - Fréquence : Temps réel
   - Limites : 1000 appels/jour (gratuit)

3. **BTS Transtats** - Historique des retards de vols aux USA
   - URL : https://www.transtats.bts.gov
   - Format : CSV (téléchargement)

### Architecture réseau

```
Internet
  │
  ├─→ Traefik (Reverse Proxy + SSL)
  │     │
  │     ├─→ dst-airlines.srv869578.hstgr.cloud → FastAPI Web App
  │     ├─→ dst-prefect.srv869578.hstgr.cloud → Prefect Server UI
  │     └─→ dst-airlines-studio.srv869578.hstgr.cloud → Supabase Studio
  │
  └─→ Docker Network
        │
        ├─→ Supabase PostgreSQL (5433)
        ├─→ Prefect Server (4201)
        ├─→ Prefect Worker
        └─→ FastAPI App (8001)
```

## 📊 Flux de données

### 1. Initialisation (première fois)

```mermaid
Lufthansa API → Countries/Cities/Airlines/Airports/Aircrafts → PostgreSQL
                     ↓
               Calculate Routes (geopy)
                     ↓
              Store in PostgreSQL
```

### 2. Pipeline quotidien

```mermaid
Prefect Scheduler (2h00 UTC)
         ↓
Lufthansa API → Flight Schedules → PostgreSQL
         ↓
OpenWeatherMap API → Weather Data → PostgreSQL
```

### 3. Mise à jour temps réel (5x par jour)

```mermaid
Prefect Scheduler (6h, 10h, 14h, 18h, 22h UTC)
         ↓
Lufthansa API → Flight Status → Update PostgreSQL
```

### 4. Entraînement ML (hebdomadaire)

```mermaid
Prefect Scheduler (Dimanche 3h00 UTC)
         ↓
PostgreSQL → Load Historical Data
         ↓
Preprocessing (One-Hot Encoding, Feature Engineering)
         ↓
Train RandomForest Models (Classification + Regression)
         ↓
Save PKL Files → FastAPI Auto-Reload
```

## 🔧 Dépannage

### Les flows ne s'exécutent pas

```bash
# Vérifier que Prefect Server est démarré
docker ps | grep prefect

# Vérifier les logs
docker logs dst-airlines-prefect-agent

# Redémarrer les services
./deploy-dst-airlines.sh restart
```

### Erreur de connexion à la base de données

```bash
# Vérifier que Supabase PostgreSQL est démarré
docker ps | grep supabase-db

# Tester la connexion
docker exec dst-airlines-supabase-db psql -U postgres -c "SELECT 1;"

# Vérifier les variables d'environnement
docker exec dst-airlines-prefect-agent env | grep PG_
```

### L'application web ne démarre pas

```bash
# Vérifier les logs
docker logs dst-airlines-web

# Vérifier que les modèles ML existent
docker exec dst-airlines-web ls -la /app/flight-delay-predictor/app/models/

# Redémarrer l'application
docker restart dst-airlines-web
```

### Erreurs API Lufthansa (Rate Limiting)

Les flows incluent une gestion automatique des erreurs de rate limiting avec :
- Retry automatique (30 secondes de délai)
- Limitation à 20 éléments par requête
- Gestion gracieuse des erreurs 403

### Vérifier l'état global du système

```bash
# Statut de tous les services
./deploy-dst-airlines.sh status

# Vérifier la santé de l'application
curl http://localhost:8001/api/health

# Vérifier Prefect
curl http://localhost:4201/api/health
```

## 🔑 APIs et authentification

### Lufthansa Developer API

1. Créer un compte sur https://developer.lufthansa.com
2. Créer une application pour obtenir Client ID et Client Secret
3. Ajouter les credentials dans `config/.env`

**Endpoints utilisés** :
- `/mds-references/countries` - Pays
- `/mds-references/cities` - Villes
- `/mds-references/airlines` - Compagnies
- `/mds-references/airports` - Aéroports
- `/mds-references/aircraft` - Avions
- `/operations/schedules` - Plannings de vols
- `/operations/flightstatus` - Statuts en temps réel

### OpenWeatherMap API

1. Créer un compte sur https://openweathermap.org
2. Générer une clé API (gratuit : 1000 appels/jour)
3. Ajouter la clé dans `config/.env`

**Endpoint utilisé** :
- `/data/2.5/weather` - Météo actuelle par coordonnées

## 📈 Métriques et performances

### Volumétrie

- **Données de référence** : ~12 000 enregistrements
- **Vols historiques** : ~100 000 enregistrements (BTS)
- **Vols temps réel** : Variable (ajout quotidien)
- **Cache météo** : ~1000 enregistrements (TTL : 24h)

### Performances d'entraînement ML

- **Classification** : ~2-5 minutes pour 10 000 vols
- **Régression** : ~3-6 minutes pour 10 000 vols
- **Accuracy** : ~75-85% (dépend du volume de données)
- **RMSE** : ~20-30 minutes (régression)

## 📝 Commandes utiles

```bash
# Production (VPS + Supabase)
./deploy-dst-airlines.sh start        # Démarrer
./deploy-dst-airlines.sh stop         # Arrêter
./deploy-dst-airlines.sh restart      # Redémarrer
./deploy-dst-airlines.sh status       # Statut
./deploy-dst-airlines.sh logs         # Logs
./deploy-dst-airlines.sh rebuild      # Rebuild
./deploy-dst-airlines.sh deploy-flows # Déployer workflows Prefect

# Local (laptop + PostgreSQL intégré)
./deploy-dst-airlines.sh start-local  # Démarrer en local
./deploy-dst-airlines.sh stop-local   # Arrêter
./deploy-dst-airlines.sh status-local # Statut
./deploy-dst-airlines.sh logs-local   # Logs
./deploy-dst-airlines.sh rebuild-local # Rebuild
./deploy-dst-airlines.sh clean-local  # Supprimer volumes

# Test des flows
./test_flow.sh                        # Menu interactif

# Initialisation
./init_database.sh                    # Créer les tables

# Docker
docker ps                             # Conteneurs actifs
docker logs -f <container>            # Suivre les logs
docker exec -it <container> bash      # Accéder au conteneur
```

## 👨‍💻 Développement

### Structure des flows Prefect

Chaque flow suit cette structure :

```python
from prefect import flow, task

@task(retries=2, retry_delay_seconds=30)
def ma_tache():
    # Logique métier
    pass

@flow(log_prints=True)
def mon_flow():
    print("[FLOW START] Début du traitement")
    ma_tache()
    print("[FLOW COMPLETE] Traitement terminé")
```

### Ajouter un nouveau flow

1. Créer le fichier dans `prefect_flows/`
2. Définir les tasks et le flow
3. Ajouter le deployment dans `deploy_flows.py`
4. Redéployer : `./deploy-dst-airlines.sh deploy-flows`

### Tests locaux

```bash
# Tester un job individuellement
docker exec dst-airlines-prefect-agent python -m src.jobs.sync_countries

# Tester un modèle ML
docker exec dst-airlines-prefect-agent python -m src.ml.ml_classification

# Tester l'application web localement
cd flight-delay-predictor/app
python app.py
```

## 📚 Documentation complémentaire

- **Guide de déploiement** : `DEPLOYMENT_GUIDE.md` (sur le serveur)
- **Guide de test des flows** : `FLOW_TESTING_GUIDE.md` (sur le serveur)
- **Configuration Supabase** : `SUPABASE_SETUP.md` (sur le serveur)
- **Documentation Prefect** : https://docs.prefect.io
- **Documentation FastAPI** : https://fastapi.tiangolo.com

## 🤝 Contribution

Pour contribuer au projet :

1. Fork le repository
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Commit les changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Push vers la branche (`git push origin feature/ma-fonctionnalite`)
5. Créer une Pull Request

## 📄 Licence

Ce projet est développé dans le cadre académique de la formation Data Engineering à Datascientest.

## 🆘 Support

Pour toute question ou problème :

1. Vérifier les logs : `./deploy-dst-airlines.sh logs`
2. Consulter la documentation dans `/docs`
3. Contacter l'équipe de développement

---

**Version** : 2.2
**Dernière mise à jour** : Janvier 2025
**Technologies** : Python 3.11, Prefect 3, FastAPI, PostgreSQL, Supabase, Docker, scikit-learn
**Modes de déploiement** : Production (VPS + Supabase) | Local (laptop + PostgreSQL intégré)
