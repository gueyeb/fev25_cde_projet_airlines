# Orchestration de Workflows : Airflow vs Prefect

> La version anglaise d'origine est archivée dans `docs/archive/ORCHESTRATION_WORKFLOW_FR.md`. Ce document devient la référence active en français.

## Résumé exécutif

Pour notre périmètre actuel (prédiction de retards avec pipelines ETL simples), **les tâches cron suffisent** pour démarrer. Si un orchestrateur complet devient nécessaire, **Prefect** est mieux adapté qu'Airflow.

## Pourquoi PAS Airflow ou Grafana ?

### Grafana
- Outil de visualisation/monitoring, **pas** un orchestrateur.
- Sert aux tableaux de bord et métriques.
- Ne peut ni planifier ni exécuter des pipelines.
- Utile plus tard pour suivre le modèle ML, mais pas pour orchestrer.

### Limites d'Airflow pour ce projet
1. **Infrastructure lourde** : webserver, scheduler, DB, executor.
2. **Mise en place complexe** : forte courbe d'apprentissage.
3. **Surdimensionné** pour des pipelines simples.
4. **Ressources élevées** : mémoire/CPU importants.
5. **DAGs verbeux** : surcharge de développement.

## Pourquoi Prefect ?

### Atouts
1. **Léger** : tourne sur une seule machine.
2. **Setup rapide** : `pip install prefect`.
3. **Natif Python** : flows = fonctions Pythons classiques.
4. **Pensé cloud-native**.
5. **Niveau gratuit généreux** (Prefect Cloud).
6. **Gestion d'erreurs moderne** : retries, logs, alertes.
7. **Workflows dynamiques** plus simples.

### Exemple de flow Prefect

```python
from prefect import flow, task

@task(retries=3, retry_delay_seconds=60)
def sync_countries():
    from src.jobs import sync_countries
    sync_countries.sync_countries()

@task(retries=3, retry_delay_seconds=60)
def sync_cities():
    from src.jobs import sync_cities
    sync_cities.sync_cities()

@flow(name="Daily Flight Data Pipeline")
def daily_pipeline():
    sync_countries()
    sync_cities()
    # Ajouter d'autres tâches…

if __name__ == "__main__":
    daily_pipeline()
```

## Paliers de recommandation

### Niveau 1 : Simple (recommandé maintenant)
- **Cron** + script de monitoring.
- Coût : 0€ – Complexité : faible – Mise en place : ~30 min.

### Niveau 2 : Orchestration légère
- **Prefect** si besoin de dépendances, retries, monitoring, workflows dynamiques.
- Effort : 2 à 4 h.

### Niveau 3 : Entreprise (non pertinent ici)
- **Airflow** uniquement si dizaines de pipelines, équipe dédiée et infra disponible.
- Effort : plusieurs jours.

## Plan d'implémentation (cron)

1. Synchronisation quotidienne à 02h00.
2. Mise à jour des statuts toutes les 4h.
3. Journalisation systématique.
4. Alertes optionnelles en cas d'échec.

## Quand migrer vers Prefect ?

- >5 pipelines différents.
- Dépendances complexes.
- Besoin d'une meilleure résilience aux échecs.
- Nécessité d'évoluer en volume.
- Besoin d'une UI de supervision.

## Comparatif des coûts

| Outil   | Coût infra | Temps d'apprentissage | Maintenance |
|---------|-----------|-----------------------|-------------|
| Cron    | 0€        | ~1 h                  | Minimale    |
| Prefect | 0–50€/mois| 4–8 h                 | Faible      |
| Airflow | 100–500€/mois | 20–40 h           | Élevée      |

## Conclusion

Commencer avec des tâches cron. Lorsque la complexité grandit, migrer vers Prefect (transition simple). Réserver Airflow aux besoins véritablement « enterprise ».
