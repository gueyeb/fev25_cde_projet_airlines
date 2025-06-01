import os
import pymongo

from config.env_loader import load_env

load_env()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB")
COLLECTION_NAME = os.getenv("WEATHER_COLLECTION_NAME", "weather")  # valeur par défaut

TTL_SECONDS = 5400  # 90 minutes

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Création de l'index TTL
result = collection.create_index(
    [("timestamp", pymongo.ASCENDING)],
    expireAfterSeconds=TTL_SECONDS
)

print(f"Index TTL créé : {result}")
