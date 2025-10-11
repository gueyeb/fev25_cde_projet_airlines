# **DST Airlines**

**Cursus concerné :** Data Engineer

**Diffficulté :** 8.5/10

# **Description détaillée :**

De nos jours, il est possible d’avoir des informations sur les vols dans le monde entier et de traquer en temps réel un avion. Nous pouvons observer ce [site](https://www.flightradar24.com/) en guise d’exemple. Le but de ce projet est de créer un outil permettant de faire des prévisions sur le retard d’un vol ou non.

| Etape | Description | Objectif | Modules / Masterclass / Templates | Conditions de validation du projet |
| :---: | :---- | ----- | ----- | :---- |
| **1** | Récolte des données | Passer par l’API de [Lufthansa](https://developer.lufthansa.com/docs) pour récupérer des données sur les vols. Vous pouvez tester les différentes routes de l’API de Lufthansa m l’aide de ce [lien](https://developer.lufthansa.com/io-docs). Vous pourrez être amené m aller puiser différentes informations comme les codes IATA. Cette étape est importante, vous devez comprendre les données que vous pouvez récupérer et faire un choix des routes m utiliser. Il y a aussi l’API de [International Airlines](https://developer.iairgroup.com/), mais il se peut que vous ayez des soucis pour y accéder.. |  Utilisation de la librairie requests ou de l’outil Postman (pour tester) Techniques de webscraping |  Fichier explicatif du traitement et des différentes données accessible (doc / pdf) Un exemple de données collectées. |
| **2** | Architecture des données | Il y a plusieurs options qui s’offrent m nous. Lors de la précédente étape, nous avons observé qu’il y a plusieurs “types” de données. Nous allons qualiﬁer des données de **ffixe** comme les informations sur les aéroports et de **variables**, les informations sur les vols. Cette diversiﬁcation de données va conduire m une utilisation de différentes bases de données. | SQL SnowFlake DBT Elasticsearch MongoDB Neo4j | Une		base		de données relationnelle Diagramme UML Un	ﬁchier		de requête		SQL	pour montrer	que	c’est bien fonctionnel Même rendu mais exemples			de requêtes Elastic/Mongo |

| 3 | Consommati on de la donnée | Ici, le but principal du projet sera de faire un algorithme de prévision de retard des avions grâce aux données que vous avez précédemment stockées dans vos Bases de données | DE120 | Algorithme	de Machine Learning |
| :---: | ----- | :---- | :---- | :---- |
| **4** | Déploiement | Il faut créer une API pour requêter ces différentes bases de données. Faire un conteneur Docker de chaque composant du projet (BDD, API) et faire un docker-compose fonctionnel. | FastAPI / Flask Docker | API FastAPI Conteneur,	Fichier yaml		du docker-compose |
| **5** | Automatisati on et Monitoring | Il faut récupérer les données de l’API Lufthansa selon un rythme bien déﬁni pour l’envoyer aux différents consommateurs de la donnée. **Créer un pipeline simple de CI pour déployer des nouveautés**  **Il faudra aussi monitorer l’application en production ainsi que les logs API** | Cronjob Airﬂow **Gitlab Prometheus Grafana** | Fichier	python	du DAG |
| **6** | Soutenance | Démonstration de leur appli et explication du raisonnement effectué lors de leur projet. | X | Soutenance Rapport |

