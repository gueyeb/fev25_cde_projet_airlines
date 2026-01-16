# Guide d'Orchestration Prefect

> Pour les paramètres spécifiques à chaque flow et les instructions localisées, consultez `prefect_flows/README.md` (FR). Ce document couvre l'exploitation globale de la plateforme.

## Vue d'ensemble

Nous utilisons **Prefect** pour orchestrer nos pipelines de données et nos entraînements ML. Prefect apporte :

- **Planification automatisée** : exécution des pipelines selon des règles cron
- **Logique de réessai** : retries automatiques en cas d'échec
- **Surveillance** : UI web pour suivre les runs
- **Journalisation centralisée** : logs consolidés par flow/tâche
- **Notifications** : alertes configurables sur les échecs

## Architecture

### Flows organisés par fonction

1. **Reference Data Flow** (`reference_data_flow.py`)
   - Synchronise pays, villes, compagnies, aéroports, avions, routes
   - Planification : **hebdomadaire (samedi 01h00 UTC)**

2. **Daily Flight Data Flow** (`flight_data_flow.py`)
   - Récupère les horaires de vols et enrichit avec la météo
   - Planification : **quotidienne (02h00 UTC)**

3. **Update Actuals Flow** (`update_actuals_flow.py`)
   - Met à jour retards/statuts temps réel + météo associée
   - Planification : **toutes les 4h de 06h à 22h UTC**

4. **ML Training Flow** (`ml_training_flow.py`)
   - Réentraîne le modèle de classification et vérifie le chargement
   - Planification : **hebdomadaire (dimanche 03h00 UTC)**

## Mise en place

### Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt

# Vérifier la version
python -c "import prefect; print(f'Prefect {prefect.__version__}')"
```

### Configuration rapide

```bash
./scripts/prefect/setup_prefect.sh
```

Le script :
1. Installe Prefect
2. Démarre le serveur local (ou se connecte à Cloud)
3. Crée le work pool
4. Crée les blocs de stockage
5. Déploie tous les flows avec leur planification

### Configuration manuelle

```bash
# Serveur local ou login Prefect Cloud
prefect server start
# ou
prefect cloud login

# Work pool process
prefect work-pool create default --type process

# Bloc de stockage local
python -c "from prefect.filesystems import LocalFileSystem; LocalFileSystem(basepath='.').save('local-storage', overwrite=True)"

# Déploiement des flows
cd prefect_flows
python deploy_flows.py
```

## Exécution des pipelines

### Démarrer l'agent

```bash
# Mode interactif
prefect agent start -q default

# Mode script (logs)
./scripts/prefect/start_agent.sh
```

> L'agent doit rester actif pour consommer les runs planifiés.

### Exécution manuelle (tests)

```bash
cd prefect_flows
python reference_data_flow.py
python flight_data_flow.py
python update_actuals_flow.py
python ml_training_flow.py
```

### Déclencher un déploiement

```bash
prefect deployment ls
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'

# Paramètres custom
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline' \
  --param target_date='2025-01-15' \
  --param weather_budget=500
```

## Résumé des planifications

| Flow | Planification | Fréquence | Objectif |
|------|---------------|-----------|----------|
| Reference Data Sync | Samedi 01h00 | Hebdo | Rafraîchir données de référence |
| Daily Flight Pipeline | Quotidien 02h00 | Quotidien | Charger nouveaux horaires + météo |
| Update Actuals | 06h–22h toutes 4h | 5×/jour | Statuts temps réel |
| ML Training | Dimanche 03h00 | Hebdo | Réentraîner les modèles |

> Tous les horaires sont en UTC.

## Monitoring

### Interface Prefect

- **Local** : http://localhost:4200
- **Cloud** : https://app.prefect.cloud

Suivi : historique, taux de succès, logs, détails par tâche, runs planifiés.

### Logs

- Agent : `logs/prefect/agent.log`
- Serveur local : `logs/prefect-server.log`
- Logs de flow : visibles dans l'UI

## Opérations courantes

- **Mettre en pause** : `prefect deployment pause 'daily-flight-data-pipeline/daily-flight-pipeline'`
- **Reprendre** : `prefect deployment resume 'daily-flight-data-pipeline/daily-flight-pipeline'`
- **Backfill historique** :
  ```python
  from prefect_flows.flight_data_flow import backfill_flight_data_flow
  backfill_flight_data_flow(
      start_date="2024-12-01",
      end_date="2024-12-31",
      weather_budget=900
  )
  ```
  > Attention aux limites API lors d'un backfill massif.
- **Redéployer après modifications** :
  ```bash
  cd prefect_flows
  python deploy_flows.py
  ```

## Dépannage

### L'agent ne récupère rien
1. `prefect agent ls`
2. `prefect work-pool ls`
3. Redémarrer l'agent (`./scripts/prefect/start_agent.sh`)

### `ModuleNotFoundError`
1. Lancer l'agent depuis la racine du projet
2. Vérifier `PYTHONPATH`
3. Activer l'environnement virtuel

### Erreurs 429 (APIs)
1. Réduire `weather_budget`
2. Augmenter `retry_delay_seconds`
3. Espacer les planifications

### Erreurs PostgreSQL (`psycopg2`)
1. Vérifier que la base tourne
2. Contrôler les variables `.prodenv`
3. S'assurer que l'agent a accès à `config/`

## Bonnes pratiques

### Cycle de dev
1. **Tester localement** : `python prefect_flows/flight_data_flow.py`
2. **Limiter la plage de dates** : `daily_flight_data_flow(target_date="2025-01-15")`
3. **Surveiller les premiers runs** via l'UI

### Mise en production
1. Utiliser Prefect Cloud si besoin de fiabilité
2. Configurer des notifications d'échec
3. Contrôler régulièrement le budget API
4. Revoir les logs chaque semaine
5. Sauvegarder la base avant gros backfills

### Passage à l'échelle
- Multiplier les agents : `prefect agent start -q default --limit 5`
- Activer l'exécution parallèle (`ConcurrentTaskRunner`)
- Déployer les agents sur une infra distante
- Activer les fonctionnalités avancées : cache de tâches, persistance des résultats, blocs personnalisés, webhooks

## Coûts

- **Prefect Cloud gratuit** : 20 000 exécutions de tâches/mois
- **Niveau payant** : 10$/mois pour 100 000 exécutions
- **Usage actuel estimé** : ~1 110 tâches/mois (dans la limite gratuite)

## Prochaines étapes

1. `./scripts/prefect/setup_prefect.sh`
2. `./scripts/prefect/start_agent.sh`
3. Ouvrir l'UI (localhost:4200)
4. Attendre le premier run planifié ou déclencher manuellement
5. Vérifier les logs pour confirmer le succès

## Ressources

- [Documentation Prefect](https://docs.prefect.io)
- [Slack Prefect](https://prefect.io/slack)
- [GitHub Prefect](https://github.com/PrefectHQ/prefect)
- [Guide Workflow](WORKFLOW_ORCHESTRATION.md)

## Support

1. Inspecter l'UI Prefect pour les détails d'erreur
2. Consulter `logs/prefect/agent.log`
3. Rechercher dans la doc Prefect
4. Demander sur le Slack Prefect
5. Créer une issue dans ce dépôt
