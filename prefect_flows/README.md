# Flows Prefect

Ce répertoire regroupe les definitions de workflows Prefect du projet DST Airlines.

## Démarrage rapide

```bash
# 1. Configurer Prefect
./scripts/prefect/setup_prefect.sh

# 2. Démarrer l'agent
./scripts/prefect/start_agent.sh
```

## Fichiers importants

### Flows de production

- **`reference_data_flow.py`** : synchronisation hebdo des référentiels (pays, villes, compagnies, aéroports, avions, routes).
- **`flight_data_flow.py`** : collecte quotidienne des horaires + météo.
- **`update_actuals_flow.py`** : mises à jour temps réel toutes les 4h.
- **`ml_training_flow.py`** : entraînement hebdomadaire des modèles.

### Configuration

- **`deploy_flows.py`** : script qui enregistre/déploie tous les flows avec leurs planifications.

## Organisation

```
prefect_flows/
├── reference_data_flow.py    # Hebdo : données de référence
├── flight_data_flow.py       # Quotidien : vols + météo
├── update_actuals_flow.py    # Toutes 4h : retards temps réel
├── ml_training_flow.py       # Hebdo : entraînement ML
└── deploy_flows.py           # Déploiement Prefect
```

## Exécution des flows

### Tests locaux (sans Prefect)

```bash
python reference_data_flow.py
python flight_data_flow.py
python update_actuals_flow.py
python ml_training_flow.py
```

### Via Prefect (planifié)

```bash
python deploy_flows.py
prefect agent start -q default

# Déclenchement manuel
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'
```

## Résumé des planifications

| Flow | Déploiement | Horaire (UTC) | Description |
|------|-------------|---------------|-------------|
| Reference Data | `weekly-reference-sync` | Sam 01h00 | Pays, villes, compagnies, aéroports, routes |
| Daily Flight | `daily-flight-pipeline` | Tous les jours 02h00 | Horaires + météo |
| Update Actuals | `hourly-actuals-update` | 06h–22h toutes 4h | Statuts temps réel |
| ML Training | `weekly-ml-training` | Dim 03h00 | Réentraînement modèles |

## Paramètres clés

- `daily_flight_data_flow` :
  - `target_date` (str) : date `YYYY-MM-DD`, défaut = aujourd'hui
  - `weather_budget` (int) : budget d'appels OWM, défaut = 900
- `ml_training_flow` :
  - `train_both_models` (bool) : entraîner regression + classification (False par défaut)
- `reference_data_sync_flow` :
  - `skip_routes` (bool) : ignorer la génération des routes

## Monitoring

- **UI Prefect** : http://localhost:4200 ou https://app.prefect.cloud
- **Logs** : `logs/prefect/`
- **Agents** : `prefect agent ls`
- **Déploiements** : `prefect deployment ls`

## Développement

### Ajouter un flow

1. Créer `mon_flow.py`.
2. Définir les tâches avec `@task`.
3. Définir le flow avec `@flow`.
4. Ajouter le déploiement dans `deploy_flows.py`.
5. `python deploy_flows.py`.

```python
from prefect import flow, task

@task(retries=2, log_prints=True)
def ma_tache():
    print("[INFO] Ma tâche")

@flow(name="mon-flow", log_prints=True)
def mon_flow():
    ma_tache()
```

### Modifier un flow existant

1. Éditer le fichier.
2. Tester : `python <flow>.py`.
3. Redéployer : `python deploy_flows.py`.
4. Redémarrer l'agent si besoin.

## Dépannage

- **Imports** : ajouter la racine au `PYTHONPATH`.
- **Connexion DB** : vérifier `config/.prodenv` et charger `source config/.prodenv`.
- **Limites API** : réduire `weather_budget`, augmenter les délais de retry, espacer la planification.

## Documentation complète

Voir [PREFECT_GUIDE.md](../PREFECT_GUIDE.md) pour les runbooks détaillés.
