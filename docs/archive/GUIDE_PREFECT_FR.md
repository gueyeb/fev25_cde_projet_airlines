# Guide d'Orchestration de Workflows avec Prefect

> **Archivé (2026-01-07) :** La documentation maintenue sur l'orchestration vit désormais dans `PREFECT_GUIDE.md` (FR) et `prefect_flows/README.md`. Ce document est conservé pour mémoire.

## Vue d'ensemble

Ce projet utilise **Prefect** pour l'orchestration des workflows afin de gérer les pipelines de données et les planifications d'entraînement ML. Prefect fournit :

- **Planification automatisée** - Exécution des pipelines selon des horaires cron
- **Logique de réessai** - Réessais automatiques en cas d'échec
- **Surveillance** - Interface web pour suivre l'exécution des pipelines
- **Journalisation** - Logs centralisés pour toutes les tâches
- **Notifications** - Alertes en cas d'échec (configurable)

## Architecture

### Flows Organisés par Fonction

Notre pipeline est divisé en 4 flows principaux :

1. **Flow Données de Référence** (`reference_data_flow.py`)
   - Synchronise les données de référence : pays, villes, compagnies, aéroports, avions, routes
   - Planification : **Hebdomadaire (Samedis à 1h00 UTC)**
   - Raison : Les données de référence changent rarement

2. **Flow Données de Vol Quotidiennes** (`flight_data_flow.py`)
   - Synchronise les horaires de vols pour des dates spécifiques
   - Enrichit avec les données météo
   - Planification : **Quotidien (2h00 UTC)**
   - Raison : L'API Lufthansa fournit une fenêtre de temps limitée pour les horaires

3. **Flow Mise à Jour Données Réelles** (`update_actuals_flow.py`)
   - Met à jour le statut des vols en temps réel (retards, heures réelles)
   - Rafraîchit la météo selon les heures réelles
   - Planification : **Toutes les 4 heures (6h-22h UTC)**
   - Raison : Les données en temps réel changent tout au long de la journée

4. **Flow Entraînement ML** (`ml_training_flow.py`)
   - Entraîne le modèle de classification
   - Valide que le modèle peut être chargé
   - Planification : **Hebdomadaire (Dimanches à 3h00 UTC)**
   - Raison : Le modèle s'améliore au fur et à mesure que les données s'accumulent

## Configuration

### Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt

# Vérifier l'installation
python -c "import prefect; print(f'Prefect {prefect.__version__}')"
```

### Configuration Rapide

Exécutez le script de configuration automatisé :

```bash
./scripts/prefect/setup_prefect.sh
```

Cela va :
1. Installer Prefect
2. Démarrer le serveur Prefect (ou se connecter à Prefect Cloud)
3. Créer le work pool
4. Créer les blocs de stockage
5. Déployer tous les flows avec leurs planifications

### Configuration Manuelle

Si vous préférez la configuration manuelle :

```bash
# 1. Démarrer le serveur Prefect (développement local)
prefect server start

# OU se connecter à Prefect Cloud (production)
prefect cloud login

# 2. Créer le work pool
prefect work-pool create default --type process

# 3. Créer le bloc de stockage
python -c "from prefect.filesystems import LocalFileSystem; LocalFileSystem(basepath='.').save('local-storage', overwrite=True)"

# 4. Déployer les flows
cd prefect_flows
python deploy_flows.py
```

## Exécution du Pipeline

### Démarrage de l'Agent

L'agent exécute les runs planifiés :

```bash
# Option 1 : Mode interactif
prefect agent start -q default

# Option 2 : Mode arrière-plan avec logs
./scripts/prefect/start_agent.sh
```

**Important :** Gardez l'agent en cours d'exécution pour que les flows planifiés s'exécutent !

### Exécution Manuelle

Exécutez les flows manuellement (utile pour les tests) :

```bash
# Depuis la racine du projet
cd prefect_flows

# Exécuter la synchronisation des données de référence
python reference_data_flow.py

# Exécuter le pipeline quotidien
python flight_data_flow.py

# Mettre à jour les données réelles des vols
python update_actuals_flow.py

# Entraîner le modèle ML
python ml_training_flow.py
```

### Déclenchement des Déploiements

Exécutez un déploiement planifié à la demande :

```bash
# Lister tous les déploiements
prefect deployment ls

# Exécuter un déploiement spécifique
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'

# Exécuter avec des paramètres personnalisés
prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline' \
  --param target_date='2025-01-15' \
  --param weather_budget=500
```

## Résumé de la Planification

| Flow | Planification | Fréquence | Objectif |
|------|--------------|-----------|----------|
| Sync Données Référence | Sam 1h00 | Hebdomadaire | Mettre à jour les données peu changeantes |
| Pipeline Vol Quotidien | Tous les jours 2h00 | Quotidien | Obtenir les nouveaux horaires de vols |
| Mise à Jour Données Réelles | 6h-22h toutes les 4h | 5x par jour | Statut des vols en temps réel |
| Entraînement ML | Dim 3h00 | Hebdomadaire | Réentraîner les modèles avec nouvelles données |

**Note :** Tous les horaires sont en UTC. Ajustez pour votre fuseau horaire.

## Surveillance

### Interface Prefect

Accédez à l'interface web :

- **Serveur Local :** http://localhost:4200
- **Prefect Cloud :** https://app.prefect.cloud

L'interface montre :
- Historique d'exécution des flows
- Taux de succès/échec
- Logs d'exécution
- Détails au niveau des tâches
- Exécutions planifiées

### Logs

Prefect écrit les logs dans :
- **Logs de l'agent :** `logs/prefect/agent.log`
- **Logs du serveur :** `logs/prefect-server.log` (serveur local uniquement)
- **Logs des flows :** Visibles dans l'interface Prefect

## Opérations Courantes

### Mettre en Pause un Déploiement

```bash
prefect deployment pause 'daily-flight-data-pipeline/daily-flight-pipeline'
```

### Reprendre un Déploiement

```bash
prefect deployment resume 'daily-flight-data-pipeline/daily-flight-pipeline'
```

### Remplissage Rétrospectif de Données Historiques

Utilisez le flow de backfill pour charger des données historiques :

```python
from prefect_flows.flight_data_flow import backfill_flight_data_flow

# Backfill des 30 derniers jours
backfill_flight_data_flow(
    start_date="2024-12-01",
    end_date="2024-12-31",
    weather_budget=900
)
```

**Attention :** Soyez prudent avec les limites de taux des API lors du backfill !

### Mettre à Jour un Déploiement

Après modification d'un flow :

```bash
cd prefect_flows
python deploy_flows.py  # Re-déploie tous les flows
```

## Dépannage

### L'Agent ne Récupère pas les Exécutions

**Symptômes :** Les exécutions planifiées restent à l'état "Scheduled"

**Solutions :**
1. Vérifier que l'agent est en cours d'exécution : `prefect agent ls`
2. Vérifier le work pool : `prefect work-pool ls`
3. Redémarrer l'agent : `./scripts/prefect/start_agent.sh`

### Erreurs d'Import

**Symptômes :** `ModuleNotFoundError` lors de l'exécution du flow

**Solutions :**
1. S'assurer que l'agent est démarré depuis la racine du projet
2. Vérifier que `PYTHONPATH` inclut le répertoire du projet
3. Vérifier que l'environnement virtuel est activé

### Limites de Taux API

**Symptômes :** Erreurs HTTP 429 des APIs Lufthansa/OpenWeatherMap

**Solutions :**
1. Réduire le paramètre `weather_budget`
2. Augmenter le délai de réessai dans les décorateurs de tâche
3. Ajuster la fréquence de planification

### Erreurs de Connexion à la Base de Données

**Symptômes :** Erreurs de connexion `psycopg2`

**Solutions :**
1. Vérifier que la base de données est en cours d'exécution
2. Vérifier les variables d'environnement dans `.prodenv`
3. S'assurer que l'agent a accès aux fichiers de configuration

## Bonnes Pratiques

### Workflow de Développement

1. **Tester les flows localement** avant de déployer
   ```bash
   python prefect_flows/flight_data_flow.py
   ```

2. **Utiliser de petites plages de dates** pour les tests
   ```python
   daily_flight_data_flow(target_date="2025-01-15")
   ```

3. **Surveiller les premières exécutions** dans l'interface Prefect

### Déploiement en Production

1. **Utiliser Prefect Cloud** pour la fiabilité
2. **Configurer les notifications** pour les échecs
3. **Surveiller les budgets API** régulièrement
4. **Revoir les logs** hebdomadairement
5. **Sauvegarder la base de données** avant les gros backfills

### Passage à l'Échelle

Quand vous avez besoin de plus :

1. **Plus de workers :** Démarrer plusieurs agents
   ```bash
   prefect agent start -q default --limit 5
   ```

2. **Exécution parallèle :** Utiliser `ConcurrentTaskRunner` dans les flows

3. **Exécution distante :** Déployer sur une infrastructure cloud

4. **Fonctionnalités avancées :**
   - Mise en cache des tâches
   - Persistance des résultats
   - Blocs personnalisés
   - Webhooks

## Considérations de Coût

### Tarification Prefect Cloud

- **Niveau gratuit :** 20 000 exécutions de tâches/mois (suffisant pour la plupart des cas)
- **Niveau payant :** 10$/mois pour 100 000 exécutions de tâches
- **Entreprise :** Tarification personnalisée

### Estimation de Notre Utilisation

Avec la planification actuelle :
- Pipeline quotidien : ~10 tâches/jour × 30 = 300 tâches/mois
- Mise à jour données réelles : ~5 tâches/jour × 5 × 30 = 750 tâches/mois
- Sync référence : ~10 tâches/semaine × 4 = 40 tâches/mois
- Entraînement ML : ~5 tâches/semaine × 4 = 20 tâches/mois

**Total : ~1 110 tâches/mois** (bien dans le niveau gratuit)

## Prochaines Étapes

1. **Exécuter la configuration :** `./scripts/prefect/setup_prefect.sh`
2. **Démarrer l'agent :** `./scripts/prefect/start_agent.sh`
3. **Surveiller l'interface :** http://localhost:4200
4. **Attendre la première exécution planifiée** ou déclencher manuellement
5. **Vérifier les logs** pour confirmer le succès

## Ressources Additionnelles

- [Documentation Prefect](https://docs.prefect.io)
- [Slack Communauté Prefect](https://prefect.io/slack)
- [GitHub Prefect](https://github.com/PrefectHQ/prefect)
- [Notre Guide Workflow](../WORKFLOW_ORCHESTRATION.md)

## Support

Si vous rencontrez des problèmes :

1. Vérifier l'interface Prefect pour les détails d'erreur
2. Revoir les logs de l'agent : `tail -f logs/prefect/agent.log`
3. Rechercher dans la documentation Prefect
4. Poser des questions dans le Slack Communauté Prefect
5. Créer une issue dans le dépôt du projet
