# Flows Prefect

Ce répertoire contient toutes les définitions de workflows Prefect pour le projet de Prédiction de Retards de Vol.

## Démarrage Rapide

```bash
# 1. Configurer Prefect
./scripts/prefect/setup_prefect.sh

# 2. Démarrer l'agent
./scripts/prefect/start_agent.sh
```

## Fichiers des Flows

### Flows de Production

- **`reference_data_flow.py`** - Synchronisation hebdomadaire des données de référence (pays, villes, compagnies, aéroports, routes)
- **`flight_data_flow.py`** - Synchronisation quotidienne des horaires de vols + enrichissement météo
- **`update_actuals_flow.py`** - Mises à jour périodiques du statut des vols en temps réel
- **`ml_training_flow.py`** - Entraînement hebdomadaire du modèle ML

### Configuration

- **`deploy_flows.py`** - Script de déploiement qui enregistre tous les flows avec leurs planifications

## Organisation des Flows

```
prefect_flows/
├── reference_data_flow.py    # Hebdomadaire : Données de référence
├── flight_data_flow.py        # Quotidien : Horaires vols + météo
├── update_actuals_flow.py     # Toutes les 4h : Mises à jour temps réel
├── ml_training_flow.py        # Hebdomadaire : Entraînement modèle
└── deploy_flows.py            # Configuration déploiement
```

## Exécution des Flows

### Test en Local (Sans Prefect)

```bash
# Tester les flows individuellement
python reference_data_flow.py
python flight_data_flow.py
python update_actuals_flow.py
python ml_training_flow.py
```

### Exécution via Prefect (Avec Planification)

```bash
# Déployer tous les flows
python deploy_flows.py

# Démarrer l'agent pour exécuter les runs planifiés
prefect agent start -q default

# Déclencher un déploiement manuellement
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'
```

## Résumé de la Planification

| Flow | Nom Déploiement | Planification | Description |
|------|----------------|---------------|-------------|
| Données Référence | `weekly-reference-sync` | Sam 1h00 | Sync pays, villes, compagnies, aéroports, routes |
| Vol Quotidien | `daily-flight-pipeline` | Quotidien 2h00 | Sync horaires vols + météo |
| Mise à Jour Réel | `hourly-actuals-update` | Toutes les 4h (6-22) | Mise à jour statut vol temps réel |
| Entraînement ML | `weekly-ml-training` | Dim 3h00 | Entraîner modèles ML |

Tous les horaires sont en UTC.

## Paramètres

### daily_flight_data_flow

- `target_date` (str): Date au format YYYY-MM-DD (par défaut : aujourd'hui)
- `weather_budget` (int): Budget d'appels API OpenWeatherMap (par défaut : 900)

### ml_training_flow

- `train_both_models` (bool): Entraîner classification et régression (par défaut : False)

### reference_data_sync_flow

- `skip_routes` (bool): Ignorer la création de routes (par défaut : False)

## Surveillance

- **Interface Prefect :** http://localhost:4200 (local) ou https://app.prefect.cloud
- **Logs :** `logs/prefect/`
- **Statut agent :** `prefect agent ls`
- **Statut déploiement :** `prefect deployment ls`

## Développement

### Ajouter un Nouveau Flow

1. Créer un nouveau fichier : `my_new_flow.py`
2. Définir les tâches avec le décorateur `@task`
3. Définir le flow avec le décorateur `@flow`
4. Ajouter le déploiement dans `deploy_flows.py`
5. Ré-exécuter le script de déploiement

Exemple :

```python
from prefect import flow, task

@task(retries=2, log_prints=True)
def my_task():
    print("[INFO] Exécution de ma tâche")
    # Votre code ici

@flow(name="my-flow", log_prints=True)
def my_flow():
    print("[FLOW START] Mon Flow")
    my_task()
    print("[FLOW COMPLETE]")
```

### Modifier des Flows Existants

1. Éditer le fichier du flow
2. Tester localement : `python <fichier_flow>.py`
3. Re-déployer : `python deploy_flows.py`
4. Redémarrer l'agent si nécessaire

## Bonnes Pratiques

1. **Toujours utiliser `log_prints=True`** dans les décorateurs pour la visibilité
2. **Ajouter des réessais** aux tâches qui appellent des APIs externes
3. **Définir des timeouts** pour les tâches longues
4. **Utiliser des noms descriptifs** pour les tâches et flows
5. **Documenter les paramètres** dans les docstrings
6. **Tester localement** avant de déployer

## Dépannage

### Erreurs d'Import

Assurez-vous d'ajouter la racine du projet au path :

```python
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

### Connexion Base de Données

Assurez-vous que les variables d'environnement sont chargées :

```bash
# Vérifier si .prodenv existe
ls -la config/.prodenv

# Charger manuellement si nécessaire
source config/.prodenv
```

### Limites de Taux API

Si vous atteignez les limites :
- Augmenter `retry_delay_seconds` dans les décorateurs de tâche
- Réduire le paramètre `weather_budget`
- Ajuster la fréquence de planification

## Documentation Complète

Voir [GUIDE_PREFECT.md](../GUIDE_PREFECT.md) pour la documentation complète.
