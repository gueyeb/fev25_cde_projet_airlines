# Application Web DST Airlines - Prédiction de Retards

Application FastAPI complète pour prédire les retards de vol à l'aide de modèles ML.

## Fonctionnalités

- **Prédictions en temps réel** : estimation des retards selon la route, l'horaire, etc.
- **Connexion PostgreSQL** : récupération des aéroports directement depuis la base.
- **Interface moderne** : UI responsive Bootstrap.
- **Prête pour le ML** : chargement automatique des modèles entraînés.
- **Conteneurisation** : pile Docker prête à l'emploi.

## Démarrage rapide

### Option 1 : Développement local (sans Docker)

1. **Installer les dépendances**
   ```bash
   cd app
   pip install -r requirements.txt
   ```
2. **Lancer les bases**
   ```bash
   # Depuis la racine du repo
   docker-compose up -d postgres mongo
   ```
3. **Exécuter FastAPI**
   ```bash
   cd app
   python app.py
   ```
4. **Accéder à l'app** : http://localhost:8000

### Option 2 : Docker Compose (recommandé)

```bash
cd flight-delay-predictor
docker compose up --build
```
Puis ouvrir http://localhost:8000.

## Structure

```
flight-delay-predictor/
├── app/
│   ├── app.py              # Entrée FastAPI
│   ├── Dockerfile          # Image backend
│   ├── requirements.txt    # Dépendances Python
│   ├── models/             # Modèles ML (PKL)
│   ├── static/             # CSS / JS
│   ├── templates/          # Templates Jinja2
│   ├── utils/              # Helpers backend
│   └── test_*.py           # Tests FastAPI
├── docker-compose.yml      # Stack backend + DB
└── README.md
```

## Endpoints principaux

- `GET /` : sert l'interface utilisateur.
- `GET /api/airports` : liste des aéroports (`[{code, name, city, country}]`).
- `POST /api/predict` : prédiction de retard (voir payload JSON d'exemple ci-dessous).
- `GET /api/health` : état de santé (`status`, `model_loaded`, `database_connected`).

```json
{
  "flight_number": "LH400",
  "airline": "LH",
  "departure_airport": "FRA",
  "arrival_airport": "JFK",
  "scheduled_departure": "2025-10-15T10:30:00"
}
```

## Intégration des modèles ML

1. Entraîner un modèle via `src/ml/`.
2. Sauvegarder en `.pkl` (joblib).
3. Copier dans `app/models/flight_delay_model.pkl`.
4. Redémarrer l'application : le modèle est chargé automatiquement (sinon mode mock).

## Variables d'environnement

Créer `app/.env` :

```env
PG_HOST=localhost
PG_PORT=5438
PG_DB=dst_airlines
PG_USER=dst_user
PG_PASSWORD=dst_password

MONGO_URI=mongodb://localhost:27018
MONGO_DB=dst_airlines
```

## Développement

- **Backend** : modifier `app/app.py`.
- **Templates** : `app/templates/index.html`.
- **Assets** : `app/static/js/script.js`, `app/static/css/styles.css`.
- **Auto-reload** : actif lors d'un `python app.py`.

## Initialisation base

```bash
docker-compose up -d          # services Postgres/Mongo
psql -h localhost -p 5438 -U dst_user -d dst_airlines -f database/migrations/1_create_tables.sql
python -m src.jobs.sync_airlines
python -m src.jobs.sync_airports
python -m src.jobs.sync_aircrafts
```

## Stack technique

- **Backend** : FastAPI, Python 3.11, SQLAlchemy.
- **Frontend** : HTML5, Bootstrap 5, JS vanilla, Chart.js.
- **Données** : PostgreSQL 15, MongoDB 7.
- **ML** : scikit-learn, pandas, numpy.
- **Déploiement** : Docker + docker-compose.

## Dépannage

- **Connexion PostgreSQL** : vérifier le port 5438 et la config `.env`.
- **Imports** : lancer depuis `flight-delay-predictor/app` pour accéder à `src/`.
- **Port occupé** : changer le port dans `app.py` ou `docker-compose.yml`.

## Suite

- [ ] Brancher un modèle réel depuis `src/ml/`
- [ ] Ajouter une authentification
- [ ] Recherche de vols avec auto-complétion
- [ ] Visualisation des retards historiques
- [ ] Déploiement cloud (AWS/Azure/GCP)
