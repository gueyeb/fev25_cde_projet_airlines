#!/bin/bash
#
# Script de Restauration PostgreSQL
# Restaure une sauvegarde de la base de données
#

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups/database"

# Vérifier qu'un fichier de sauvegarde est fourni
if [ $# -eq 0 ]; then
    echo "[ERROR] Veuillez spécifier un fichier de sauvegarde"
    echo "Usage: $0 <fichier_sauvegarde.sql.gz>"
    echo ""
    echo "Sauvegardes disponibles:"
    ls -lh "${BACKUP_DIR}"/backup_*.sql.gz 2>/dev/null || echo "  Aucune sauvegarde trouvée"
    exit 1
fi

BACKUP_FILE="$1"

# Vérifier que le fichier existe
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Fichier non trouvé: ${BACKUP_FILE}"
    exit 1
fi

# Charger les variables d'environnement
if [ -f "${PROJECT_DIR}/config/.prodenv" ]; then
    set -a
    source "${PROJECT_DIR}/config/.prodenv"
    set +a
else
    echo "[ERROR] Fichier .prodenv non trouvé"
    exit 1
fi

echo "[WARNING] Cette opération va ÉCRASER toutes les données de la base ${PG_DB}"
echo "[WARNING] Host: ${PG_HOST}"
echo "[WARNING] Fichier: ${BACKUP_FILE}"
echo ""
read -p "Êtes-vous sûr de vouloir continuer? (tapez 'yes' pour confirmer): " -r

if [ "$REPLY" != "yes" ]; then
    echo "[CANCELLED] Restauration annulée"
    exit 0
fi

# Créer une sauvegarde de sécurité avant restauration
echo "[INFO] Création d'une sauvegarde de sécurité..."
./scripts/backup/backup_database.sh

# Décompresser si nécessaire
TEMP_FILE="${BACKUP_FILE}"
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    echo "[INFO] Décompression de la sauvegarde..."
    TEMP_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "${BACKUP_FILE}" > "${TEMP_FILE}"
fi

# Restaurer la base de données
echo "[INFO] Restauration de la base de données..."
PGPASSWORD="${PG_PASSWORD}" psql \
    -h "${PG_HOST}" \
    -p "${PG_PORT}" \
    -U "${PG_USER}" \
    -d "${PG_DB}" \
    < "${TEMP_FILE}"

# Nettoyer le fichier temporaire
if [ "${TEMP_FILE}" != "${BACKUP_FILE}" ]; then
    rm "${TEMP_FILE}"
fi

echo "[SUCCESS] Restauration terminée avec succès"
