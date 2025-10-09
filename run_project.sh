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

pause_between() {
  local secs="$1"
  echo "⏳ Pause ${secs}s ..."
  sleep "${secs}"
}

### --- Chemins scripts Python --------------------------------------------------
MIGRATIONS_DIR="${PROJECT_DIR}/migrations"
SCRIPTS_DIR="${PROJECT_DIR}/jobs"

PREPARE_DB="${MIGRATIONS_DIR}/prepare_db.py"

SYNC_AIRCRAFTS="${SCRIPTS_DIR}/sync_aircrafts.py"
SYNC_AIRLINES="${SCRIPTS_DIR}/sync_airlines.py"
SYNC_AIRPORTS="${SCRIPTS_DIR}/sync_airports.py"
SYNC_COUNTRIES="${SCRIPTS_DIR}/sync_countries.py"

SYNC_LH_HISTORY="${SCRIPTS_DIR}/sync_flight_history.py"
ENRICH_WEATHER="${SCRIPTS_DIR}/enrich_weather_programmed.py"

[[ -f "$PREPARE_DB" ]]      || die "Script manquant: $PREPARE_DB"
[[ -f "$SYNC_AIRCRAFTS" ]]  || die "Script manquant: $SYNC_AIRCRAFTS"
[[ -f "$SYNC_AIRLINES" ]]   || die "Script manquant: $SYNC_AIRLINES"
[[ -f "$SYNC_AIRPORTS" ]]   || die "Script manquant: $SYNC_AIRPORTS"
[[ -f "$SYNC_COUNTRIES" ]]  || die "Script manquant: $SYNC_COUNTRIES"
[[ -f "$SYNC_LH_HISTORY" ]] || die "Script manquant: $SYNC_LH_HISTORY"
[[ -f "$ENRICH_WEATHER" ]]  || die "Script manquant: $ENRICH_WEATHER"

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
echo "🧱 Préparation de la base (création des tables)..."
if [[ -n "$DOTENV_PATH" ]]; then
  run_py "$PREPARE_DB" --env "$DOTENV_PATH" --tables aircrafts,airlines,airports,countries,lufthansa_flight_history,weather_hourly_cache
else
  run_py "$PREPARE_DB"
fi
pause_between "$SLEEP_BETWEEN"

### --- 4) Chargement des données de référence ---------------------------------
echo "📦 Chargement des tables de référence (ordre imposé) ..."
run_py "$SYNC_AIRCRAFTS"
pause_between "$SLEEP_BETWEEN"

run_py "$SYNC_AIRLINES"
pause_between "$SLEEP_BETWEEN"

run_py "$SYNC_AIRPORTS"
pause_between "$SLEEP_BETWEEN"

run_py "$SYNC_COUNTRIES"
pause_between "$SLEEP_BETWEEN"

### --- 5) Schedules LH + Météo programmée -------------------------------------
echo "🛫 Synchronisation des Schedules Lufthansa (${TARGET_DATE}) ..."
# Si ton script accepte --date, décommente la ligne suivante et commente l’autre.
run_py "$SYNC_LH_HISTORY" --date "$TARGET_DATE"
# run_py "$SYNC_LH_HISTORY"
pause_between "$SLEEP_BETWEEN"

echo "🌦️  Enrichissement météo (programmée) pour ${TARGET_DATE} ..."
run_py "$ENRICH_WEATHER" --date "$TARGET_DATE" --budget "$BUDGET_HOURLY"
pause_between "$SLEEP_BETWEEN"

echo "✅ Pipeline terminé avec succès."
