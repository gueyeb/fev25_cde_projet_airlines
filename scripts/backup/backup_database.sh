#!/bin/bash
#
# Script de Sauvegarde PostgreSQL
# Crée une sauvegarde complète de la base de données
#

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Créer le répertoire de sauvegarde
mkdir -p "${BACKUP_DIR}"

# Charger les variables d'environnement
if [ -f "${PROJECT_DIR}/config/.prodenv" ]; then
    set -a
    source "${PROJECT_DIR}/config/.prodenv"
    set +a
else
    echo "[ERROR] Fichier .prodenv non trouvé"
    exit 1
fi

echo "[INFO] Démarrage de la sauvegarde de la base de données..."
echo "[INFO] Host: ${PG_HOST}"
echo "[INFO] Database: ${PG_DB}"

# Nom du fichier de sauvegarde
BACKUP_FILE="${BACKUP_DIR}/backup_${PG_DB}_${TIMESTAMP}.sql"

# Créer la sauvegarde
echo "[INFO] Création de la sauvegarde..."
PGPASSWORD="${PG_PASSWORD}" pg_dump \
    -h "${PG_HOST}" \
    -p "${PG_PORT}" \
    -U "${PG_USER}" \
    -d "${PG_DB}" \
    --format=plain \
    --no-owner \
    --no-acl \
    > "${BACKUP_FILE}"

# Compresser la sauvegarde
echo "[INFO] Compression de la sauvegarde..."
gzip "${BACKUP_FILE}"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Afficher la taille
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[SUCCESS] Sauvegarde créée: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Nettoyer les anciennes sauvegardes (garder les 7 dernières)
echo "[INFO] Nettoyage des anciennes sauvegardes..."
cd "${BACKUP_DIR}"
ls -t backup_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm
echo "[SUCCESS] Nettoyage terminé"

# Optionnel: Uploader vers le cloud (à décommenter si nécessaire)
# echo "[INFO] Upload vers S3/GCS..."
# aws s3 cp "${BACKUP_FILE}" "s3://your-bucket/backups/"
# # ou
# gsutil cp "${BACKUP_FILE}" "gs://your-bucket/backups/"

echo ""
echo "[COMPLETE] Sauvegarde terminée avec succès"
echo "Fichier: ${BACKUP_FILE}"
echo ""
echo "Pour restaurer:"
echo "  gunzip ${BACKUP_FILE}"
echo "  psql -h \$PG_HOST -U \$PG_USER -d \$PG_DB < ${BACKUP_FILE%.gz}"
