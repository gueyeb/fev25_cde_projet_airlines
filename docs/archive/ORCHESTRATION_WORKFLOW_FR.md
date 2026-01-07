# Orchestration de Workflows : Airflow vs Prefect

> **Archivé (2026-01-07) :** Consultez `WORKFLOW_ORCHESTRATION.md` pour la version maintenue de cette aide à la décision. Ce fichier n'est plus mis à jour.

## Résumé Exécutif

Pour la portée actuelle de votre projet (prédiction de retards de vol avec des pipelines ETL simples), **nous recommandons de commencer avec des tâches cron** ou un planificateur léger. Si vous avez besoin d'un véritable outil d'orchestration de workflows, **Prefect** est le meilleur choix par rapport à Airflow pour votre cas d'usage.

## Pourquoi PAS Airflow ou Grafana ?

### Grafana
- **Grafana est un outil de surveillance/visualisation, PAS un orchestrateur de workflow**
- Il est utilisé pour les tableaux de bord et la visualisation de métriques
- Ne peut pas planifier ou exécuter des pipelines de données
- Vous pourriez utiliser Grafana plus tard pour surveiller les performances de votre modèle ML, mais il n'orchestrera pas les workflows

### Inconvénients d'Airflow pour les Projets Simples
1. **Infrastructure lourde** - Nécessite plusieurs composants (webserver, scheduler, database, executor)
2. **Configuration complexe** - Courbe d'apprentissage abrupte
3. **Sur-ingénierie** pour des pipelines simples
4. **Gourmand en ressources** - Nécessite beaucoup de mémoire et CPU
5. **Surcharge de développement DAG** - Les DAGs Python peuvent être verbeux

## Pourquoi Prefect ?

### Avantages
1. **Léger** - Peut fonctionner sur une seule machine
2. **Configuration simple** - `pip install prefect` et vous êtes prêt
3. **Natif Python** - Écrivez les flows comme des fonctions Python normales
4. **Design moderne** - Construit pour les workflows cloud-native
5. **Niveau gratuit** - Prefect Cloud a un niveau gratuit généreux
6. **Meilleure gestion des erreurs** - Réessais automatiques, journalisation et alertes
7. **Workflows dynamiques** - Plus facile de créer des pipelines conditionnels

### Exemple de Flow Prefect

```python
from prefect import flow, task
from datetime import timedelta

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
    # Ajouter plus de tâches...

if __name__ == "__main__":
    daily_pipeline()
```

## Recommandations par Niveau

### Niveau 1 : Commencer Simple (Recommandé pour l'instant)
Utiliser **tâches cron** avec un script de surveillance :
- Coût : Gratuit
- Complexité : Faible
- Temps de configuration : 30 minutes
- Bon pour : Tâches simples et planifiées

### Niveau 2 : Orchestration Légère
Utiliser **Prefect** si vous avez besoin de :
- Dépendances de tâches
- Logique de réessai
- Meilleure surveillance
- Workflows dynamiques
- Temps de configuration : 2-4 heures

### Niveau 3 : Entreprise (PAS recommandé pour votre échelle)
Utiliser **Airflow** seulement si vous avez :
- Des dizaines de pipelines complexes
- Une équipe d'ingénieurs de données
- Infrastructure dédiée
- Temps de configuration : Plusieurs jours

## Plan d'Implémentation

Nous configurerons un planificateur simple basé sur cron qui :
1. Exécute la synchronisation quotidienne des données à 2h du matin
2. Met à jour les statuts de vol toutes les 4 heures
3. Enregistre tous les résultats d'exécution
4. Envoie des alertes en cas d'échec (optionnel)

## Quand Passer à Prefect

Envisagez Prefect quand vous :
- Avez plus de 5 pipelines différents
- Avez besoin de dépendances de tâches complexes
- Voulez une meilleure gestion des échecs
- Devez mettre à l'échelle l'exécution
- Voulez une interface pour surveiller les exécutions

## Comparaison des Coûts

| Outil | Coût Infrastructure | Temps Apprentissage | Maintenance |
|-------|-------------------|---------------------|-------------|
| Cron | 0€ | 1 heure | Minimale |
| Prefect | 0-50€/mois | 4-8 heures | Faible |
| Airflow | 100-500€/mois | 20-40 heures | Élevée |

## Conclusion

Commencez avec des tâches cron maintenant. Si votre projet grandit et que vous avez besoin d'une orchestration plus sophistiquée, migrez vers Prefect (la migration est simple). Évitez Airflow sauf si vous avez des exigences d'entreprise.
