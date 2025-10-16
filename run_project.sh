#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# run_pipeline.sh
# ------------------------------------------------------------------------------
# Orchestration complète :
#   1) Vérifie la présence de Docker ; sinon explique comment l’installer.
#   2) --env=host : démarre/valide la base via docker-compose (gère les conflits de nom).
#      --env=prod : ne lance pas Docker (on suppose une base déjà accessible).
#   3) Exécute migrations/prepare_db.py (lit .env) pour créer les tables.
#   4) Charge les données de référence : aircrafts, airlines, airports, countries.
#   5) Remplit lufthansa_flight_history (schedules) puis weather_hourly_cache.
#
# Options:
#   --env=host|prod        (obligatoire)   Mode exécution (host => docker compose).
#   --project-dir=...      (optionnel)     Répertoire du projet (défaut: dossier courant).
#   --python=/chemin/py    (optionnel)     Binaire Python (défaut: auto: python3 puis python).
#   --sleep=SECS           (optionnel)     Pause entre scripts (défaut: 20).
#   --date=YYYY-MM-DD      (optionnel)     Date à traiter (défaut: today).
#   --dotenv=./.env        (optionnel)     Chemin du fichier .env pour prepare_db.py.
#   --db-container=name    (optionnel)     Nom du conteneur PostgreSQL (défaut: postgres_dst).
#   --force-recreate       (optionnel)     Force un down/up du stack docker-compose.
#
# Exemples:
#   ./run_pipeline.sh --env=host
#   ./run_pipeline.sh --env=host --db-container=postgres_dst --force-recreate
#   ./run_pipeline.sh --env=prod --sleep=10 --date=2025-09-28
# ==============================================================================

### --- Paramètres par défaut ---------------------------------------------------
ENV_MODE=""                         # host | prod (obligatoire)
PROJECT_DIR="$(pwd)"
PY_BIN=""
SLEEP_BETWEEN="20"
TARGET_DATE="$(date +%F)"
DOTENV_PATH=""
DB_CONTAINER_NAME="postgres_dst"
FORCE_RECREATE="false"
BUDGET_HOURLY=1000  # Nombre max de requêtes météo par heure (Open-Meteo)

### --- Parsing des arguments ---------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --env=*)            ENV_MODE="${arg#*=}"; shift ;;
    --project-dir=*)    PROJECT_DIR="${arg#*=}"; shift ;;
    --python=*)         PY_BIN="${arg#*=}"; shift ;;
    --sleep=*)          SLEEP_BETWEEN="${arg#*=}"; shift ;;
    --date=*)           TARGET_DATE="${arg#*=}"; shift ;;
    --dotenv=*)         DOTENV_PATH="${arg#*=}"; shift ;;
    --db-container=*)   DB_CONTAINER_NAME="${arg#*=}"; shift ;;
    --budget=*)   BUDGET_HOURLY="${arg#*=}"; shift ;;
    --force-recreate)   FORCE_RECREATE="true"; shift ;;
    --help|-h)          sed -n '1,160p' "$0"; exit 0 ;;
    *) echo "Argument inconnu: $arg"; echo "Utilise --help pour l’aide."; exit 1 ;;
  esac
done

if [[ -z "$ENV_MODE" ]]; then
  echo "❌ Paramètre manquant: --env=host|prod"
  exit 1
fi


export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH:-}"

### --- Résolution du Python binaire -------------------------------------------
if [[ -z "$PY_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then PY_BIN="python3"
  elif command -v python  >/dev/null 2>&1; then PY_BIN="python"
  else echo "❌ Python introuvable. Spécifie --python=/chemin/vers/python"; exit 1
  fi
fi

### --- Fonctions utilitaires ---------------------------------------------------
die() { echo "❌ $*" >&2; exit 1; }

need_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "⚠️  Docker n'est pas installé."
    echo "Veuillez installer Docker puis relancer ce script."
    echo "👉 https://docs.docker.com/engine/install/"
    exit 1
  fi
}

container_exists() {
  # 0 si existe (peu importe l'état), 1 sinon
  docker ps -a --format '{{.Names}}' | grep -Fxq "$DB_CONTAINER_NAME"
}

container_is_running() {
  # 0 si RUNNING, 1 sinon
  docker ps --format '{{.Names}}' | grep -Fxq "$DB_CONTAINER_NAME"
}

docker_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    die "Ni 'docker compose' ni 'docker-compose' n'est disponible."
  fi
}

docker_compose_up() {
  local compose_file="${PROJECT_DIR}/docker-compose.yml"
  [[ -f "$compose_file" ]] || die "Fichier docker-compose.yml introuvable dans ${PROJECT_DIR}"

  local dccmd; dccmd="$(docker_compose_cmd)"

  # Gestion du conteneur déjà présent
  if container_exists; then
    if container_is_running; then
      if [[ "$FORCE_RECREATE" == "true" ]]; then
        echo "♻️  --force-recreate demandé : down puis up..."
        (cd "$PROJECT_DIR" && $dccmd down)
        (cd "$PROJECT_DIR" && $dccmd up -d)
      else
        echo "✅ Conteneur '$DB_CONTAINER_NAME' déjà en cours d'exécution. On continue sans relancer docker-compose."
      fi
    else
      echo "🧹 Conteneur '$DB_CONTAINER_NAME' existe mais est arrêté → suppression..."
      docker rm -f "$DB_CONTAINER_NAME" >/dev/null
      echo "🚀 Lancement docker-compose..."
      (cd "$PROJECT_DIR" && $dccmd up -d)
    fi
  else
    echo "🚀 Lancement docker-compose (premier démarrage)..."
    (cd "$PROJECT_DIR" && $dccmd up -d)
  fi
}

run_py() {
  local script="$1"; shift || true
  echo "▶️  ${PY_BIN} ${script} $*"
  "${PY_BIN}" "${script}" "$@"
}

run_py_module() {
  local module="$1"; shift || true
  echo "▶️  ${PY_BIN} -m ${module} $*"
  "${PY_BIN}" -m "${module}" "$@"
}

pause_between() {
  local secs="$1"
  echo "⏳ Pause ${secs}s ..."
  sleep "${secs}"
}

### --- Chemins scripts Python --------------------------------------------------
DB_MIGRATIONS_DIR="${PROJECT_DIR}/database/migrations"
JOBS_DIR="${PROJECT_DIR}/src/jobs"

# Migration SQL (pas de prepare_db.py, on utilise le fichier SQL directement)
DB_SCHEMA="${DB_MIGRATIONS_DIR}/1_create_tables.sql"

# Jobs de synchronisation (modules Python à exécuter avec -m)
SYNC_COUNTRIES="src.jobs.sync_countries"
SYNC_CITIES="src.jobs.sync_cities"
SYNC_AIRLINES="src.jobs.sync_airlines"
SYNC_AIRPORTS="src.jobs.sync_airports"
SYNC_AIRCRAFTS="src.jobs.sync_aircrafts"
CREATE_ROUTES="src.jobs.create_routes"
SYNC_LH_HISTORY="src.jobs.sync_flight_history"
ENRICH_WEATHER="src.jobs.enrich_weather_programmed"

# Vérification de l'existence des fichiers Python
[[ -f "${JOBS_DIR}/sync_countries.py" ]]               || die "Script manquant: ${JOBS_DIR}/sync_countries.py"
[[ -f "${JOBS_DIR}/sync_cities.py" ]]                  || die "Script manquant: ${JOBS_DIR}/sync_cities.py"
[[ -f "${JOBS_DIR}/sync_airlines.py" ]]                || die "Script manquant: ${JOBS_DIR}/sync_airlines.py"
[[ -f "${JOBS_DIR}/sync_airports.py" ]]                || die "Script manquant: ${JOBS_DIR}/sync_airports.py"
[[ -f "${JOBS_DIR}/sync_aircrafts.py" ]]               || die "Script manquant: ${JOBS_DIR}/sync_aircrafts.py"
[[ -f "${JOBS_DIR}/create_routes.py" ]]                || die "Script manquant: ${JOBS_DIR}/create_routes.py"
[[ -f "${JOBS_DIR}/sync_flight_history.py" ]]          || die "Script manquant: ${JOBS_DIR}/sync_flight_history.py"
[[ -f "${JOBS_DIR}/enrich_weather_programmed.py" ]]    || die "Script manquant: ${JOBS_DIR}/enrich_weather_programmed.py"

### --- 1) Vérifier Docker -----------------------------------------------------
need_docker

### --- 2) Mode env ------------------------------------------------------------
case "$ENV_MODE" in
  host)
    echo "🌐 Mode --env=host : gestion du stack docker-compose ..."
    docker_compose_up
    ;;
  prod)
    echo "🏭 Mode --env=prod : pas de docker-compose (on suppose une base accessible)."
    ;;
  *)
    die "--env doit être 'host' ou 'prod'"
    ;;
esac

### --- 3) Préparation DB (migrations/DDL) -------------------------------------
echo "🧱 Préparation de la base (création des tables via SQL)..."
echo "ℹ️  Schéma SQL: ${DB_SCHEMA}"
echo "⚠️  IMPORTANT: Assurez-vous d'avoir exécuté le schéma SQL manuellement :"
echo "   psql -h \$PG_HOST -p \$PG_PORT -U \$PG_USER -d \$PG_DB -f ${DB_SCHEMA}"
echo "   ou via un client PostgreSQL (DBeaver, pgAdmin, etc.)"
echo ""
read -p "Les tables sont-elles créées ? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    die "Veuillez créer les tables avant de continuer."
fi
pause_between 2

### --- 4) Chargement des données de référence ---------------------------------
echo "📦 Chargement des tables de référence (ordre imposé) ..."

echo "🌍 1/6 - Synchronisation des pays..."
run_py_module "$SYNC_COUNTRIES"
pause_between "$SLEEP_BETWEEN"

echo "🏙️  2/6 - Synchronisation des villes..."
run_py_module "$SYNC_CITIES"
pause_between "$SLEEP_BETWEEN"

echo "✈️  3/6 - Synchronisation des compagnies aériennes..."
run_py_module "$SYNC_AIRLINES"
pause_between "$SLEEP_BETWEEN"

echo "🛬 4/6 - Synchronisation des aéroports..."
run_py_module "$SYNC_AIRPORTS"
pause_between "$SLEEP_BETWEEN"

echo "🛩️  5/6 - Synchronisation des types d'avions..."
run_py_module "$SYNC_AIRCRAFTS"
pause_between "$SLEEP_BETWEEN"

echo "🗺️  6/6 - Création des routes avec calcul de distances..."
run_py_module "$CREATE_ROUTES"
pause_between "$SLEEP_BETWEEN"

### --- 5) Schedules LH + Météo programmée -------------------------------------
echo "🛫 Synchronisation de l'historique des vols (${TARGET_DATE}) ..."
run_py_module "$SYNC_LH_HISTORY"
pause_between "$SLEEP_BETWEEN"

echo "🌦️  Enrichissement météo (programmée) pour ${TARGET_DATE} ..."
# Note: Vérifier si le script accepte les arguments --date et --budget
if [[ -n "$TARGET_DATE" ]] && [[ "$TARGET_DATE" != "$(date +%F)" ]]; then
    run_py_module "$ENRICH_WEATHER" --date "$TARGET_DATE" --budget "$BUDGET_HOURLY"
else
    run_py_module "$ENRICH_WEATHER"
fi
pause_between "$SLEEP_BETWEEN"

echo ""
echo "✅ Pipeline terminé avec succès."
echo ""
echo "📋 Récapitulatif :"
echo "  - Tables de référence synchronisées (countries, cities, airlines, airports, aircrafts)"
echo "  - Routes créées avec calcul de distances"
echo "  - Historique des vols synchronisé"
echo "  - Données météo enrichies"
echo ""
echo "🚀 Prochaines étapes :"
echo "  1. Entraîner le modèle ML : python -m src.ml.ml_classification"
echo "  2. Lancer l'application web : cd flight-delay-predictor/app && python app.py"
