#!/bin/bash

# EquipeMed Rootless Upgrade Script
# Safe upgrade flow for rootless Docker deployments (non-root user)

set -Eeuo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
  echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

print_info() {
  echo -e "${BLUE}ℹ${NC} $1"
}

print_step() {
  echo ""
  echo -e "${BLUE}==>${NC} $1"
}

# Defaults (override via env vars when needed)
APP_SERVICE="${APP_SERVICE:-eqmd}"
DB_SERVICE="${DB_SERVICE:-postgres}"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-./backups}"
HEALTH_PATH="${HEALTH_PATH:-/health/}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-90}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-3}"
SKIP_DB_BACKUP="${SKIP_DB_BACKUP:-0}"
SKIP_COLLECTSTATIC="${SKIP_COLLECTSTATIC:-0}"
SKIP_SITE_CONFIGURE="${SKIP_SITE_CONFIGURE:-0}"
FORCE_BUILD="${FORCE_BUILD:-0}"
DRY_RUN="${DRY_RUN:-0}"

for arg in "$@"; do
  case "$arg" in
    --dry-run|-n)
      DRY_RUN=1
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./upgrade-rootless.sh [--dry-run|-n] [--help|-h]

Options:
  --dry-run, -n   Show what would be executed without applying changes.
  --help, -h      Show this help message.

Environment overrides (optional):
  COMPOSE_FILE, ENV_FILE, APP_SERVICE, DB_SERVICE,
  FORCE_BUILD, SKIP_DB_BACKUP, SKIP_COLLECTSTATIC,
  SKIP_SITE_CONFIGURE, HEALTH_URL, HOST_PORT.
EOF
      exit 0
      ;;
    *)
      print_error "Unknown argument: $arg"
      print_info "Use --help to see available options."
      exit 1
      ;;
  esac
done

# Compose file selection
if [[ -n "${COMPOSE_FILE:-}" ]]; then
  SELECTED_COMPOSE_FILE="$COMPOSE_FILE"
else
  SELECTED_COMPOSE_FILE="docker-compose.rootless.yml"
fi

# Env-file selection
if [[ -n "${ENV_FILE:-}" ]]; then
  SELECTED_ENV_FILE="$ENV_FILE"
elif [[ -f ".env.rootless" ]]; then
  SELECTED_ENV_FILE=".env.rootless"
elif [[ -f ".env" ]]; then
  SELECTED_ENV_FILE=".env"
else
  SELECTED_ENV_FILE=""
fi

COMPOSE_OPTS=()
if [[ -n "$SELECTED_COMPOSE_FILE" ]]; then
  if [[ "$SELECTED_COMPOSE_FILE" == *":"* ]]; then
    IFS=':' read -ra FILES <<< "$SELECTED_COMPOSE_FILE"
    for file in "${FILES[@]}"; do
      [[ -n "$file" ]] || continue
      if [[ ! -f "$file" ]]; then
        print_error "Compose file not found: $file"
        exit 1
      fi
      COMPOSE_OPTS+=("-f" "$file")
    done
  else
    if [[ ! -f "$SELECTED_COMPOSE_FILE" ]]; then
      print_error "Compose file not found: $SELECTED_COMPOSE_FILE"
      print_info "Set COMPOSE_FILE=<your-rootless-compose-file> and try again."
      exit 1
    fi
    COMPOSE_OPTS+=("-f" "$SELECTED_COMPOSE_FILE")
  fi
fi

if [[ -n "$SELECTED_ENV_FILE" ]]; then
  if [[ ! -f "$SELECTED_ENV_FILE" ]]; then
    print_error "Env file not found: $SELECTED_ENV_FILE"
    exit 1
  fi
  COMPOSE_OPTS+=("--env-file" "$SELECTED_ENV_FILE")
fi

compose_cmd() {
  docker compose "${COMPOSE_OPTS[@]}" "$@"
}

wait_for_health() {
  local url="$1"
  local timeout="$2"
  local interval="$3"
  local attempts=$((timeout / interval))

  for ((i = 1; i <= attempts; i++)); do
    if curl -f -s "$url" >/dev/null; then
      return 0
    fi
    sleep "$interval"
  done

  return 1
}

rollback_to_backup_image() {
  if [[ -z "${BACKUP_IMAGE:-}" ]]; then
    print_error "No backup image available for rollback"
    return 1
  fi

  print_warning "Attempting rollback to backup image: $BACKUP_IMAGE"
  EQMD_IMAGE="$BACKUP_IMAGE" compose_cmd up -d --no-build "$APP_SERVICE"

  if wait_for_health "$HEALTH_URL" "$HEALTH_TIMEOUT_SECONDS" "$HEALTH_INTERVAL_SECONDS"; then
    print_status "Rollback completed successfully"
    return 0
  fi

  print_error "Rollback failed - manual intervention required"
  return 1
}

echo "🚀 Starting EquipeMed rootless upgrade..."
if [[ "$DRY_RUN" == "1" ]]; then
  print_warning "Running in DRY-RUN mode (no changes will be applied)"
fi

# Safety checks
if [[ $EUID -eq 0 ]]; then
  print_error "Do not run this script as root. Use the rootless user (e.g., eqmdr)."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  print_error "docker is not installed or not in PATH"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  print_error "curl is required for health checks"
  exit 1
fi

print_step "Environment checks"
CURRENT_USER="$(id -un)"
print_status "Running as user: $CURRENT_USER"
print_status "Compose options: ${COMPOSE_OPTS[*]}"

if docker info --format '{{json .SecurityOptions}}' 2>/dev/null | grep -qi rootless; then
  print_status "Docker daemon reports rootless mode"
else
  print_warning "Docker daemon does not appear to be rootless (continuing anyway)"
fi

# Load env variables (if file exists)
if [[ -n "$SELECTED_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SELECTED_ENV_FILE"
  set +a
  print_status "Loaded environment from: $SELECTED_ENV_FILE"
else
  print_warning "No env file loaded; relying on current shell environment"
fi

HOST_PORT="${HOST_PORT:-8778}"
HEALTH_URL="${HEALTH_URL:-http://localhost:${HOST_PORT}${HEALTH_PATH}}"
POSTGRES_USER="${POSTGRES_USER:-eqmd_user}"
POSTGRES_DB="${POSTGRES_DB:-eqmd_db}"

# Validate required services exist
SERVICES="$(compose_cmd config --services)"
if ! echo "$SERVICES" | grep -qx "$APP_SERVICE"; then
  print_error "Service '$APP_SERVICE' not found in compose configuration"
  exit 1
fi

DB_SERVICE_EXISTS=false
if echo "$SERVICES" | grep -qx "$DB_SERVICE"; then
  DB_SERVICE_EXISTS=true
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
UPGRADE_BACKUP_DIR="${BACKUP_BASE_DIR}/rootless-upgrade-${TIMESTAMP}"

if [[ "$DRY_RUN" == "1" ]]; then
  PREVIEW_CONTAINER_ID="$(compose_cmd ps -q "$APP_SERVICE" | head -1 || true)"
  PREVIEW_CURRENT_IMAGE=""
  PREVIEW_BACKUP_IMAGE=""

  if [[ -n "$PREVIEW_CONTAINER_ID" ]]; then
    PREVIEW_CURRENT_IMAGE="$(docker inspect "$PREVIEW_CONTAINER_ID" --format '{{.Config.Image}}' 2>/dev/null || true)"
  fi

  if [[ -n "$PREVIEW_CURRENT_IMAGE" ]]; then
    PREVIEW_BACKUP_IMAGE="eqmd-rootless-backup:${TIMESTAMP}"
  fi

  print_step "Dry-run execution plan"
  echo "- Would use compose: docker compose ${COMPOSE_OPTS[*]}"
  echo "- Would create backup dir: $UPGRADE_BACKUP_DIR"
  if [[ -n "$SELECTED_ENV_FILE" ]]; then
    echo "- Would snapshot env file: $SELECTED_ENV_FILE"
  fi
  if [[ -n "$PREVIEW_CURRENT_IMAGE" ]]; then
    echo "- Would tag current image for rollback: $PREVIEW_CURRENT_IMAGE -> $PREVIEW_BACKUP_IMAGE"
  else
    echo "- Would skip image backup (no running '$APP_SERVICE' container detected)"
  fi

  if [[ "$SKIP_DB_BACKUP" == "1" ]]; then
    echo "- DB backup: skipped (SKIP_DB_BACKUP=1)"
  elif [[ "$DB_SERVICE_EXISTS" == "true" ]]; then
    echo "- Would run DB backup via '$DB_SERVICE' (pg_dump -Fc)"
  else
    echo "- DB backup: skipped (service '$DB_SERVICE' not found in compose config)"
  fi

  if [[ "$FORCE_BUILD" == "1" ]]; then
    echo "- Image update strategy: local build (FORCE_BUILD=1)"
  elif [[ -n "${EQMD_IMAGE:-}" ]]; then
    echo "- Image update strategy: pull '$EQMD_IMAGE' (fallback: local build)"
  else
    echo "- Image update strategy: compose pull '$APP_SERVICE' (fallback: local build)"
  fi

  echo "- Would deploy: docker compose ${COMPOSE_OPTS[*]} up -d $APP_SERVICE"
  echo "- Would run migrations: python manage.py migrate --noinput"

  if [[ "$SKIP_SITE_CONFIGURE" == "1" ]]; then
    echo "- Would skip configure_django_site (SKIP_SITE_CONFIGURE=1)"
  else
    echo "- Would run configure_django_site (if command exists)"
  fi

  if [[ "$SKIP_COLLECTSTATIC" == "1" ]]; then
    echo "- Would skip collectstatic (SKIP_COLLECTSTATIC=1)"
  else
    echo "- Would run collectstatic --noinput"
  fi

  echo "- Would health-check: $HEALTH_URL"
  if [[ -n "$PREVIEW_BACKUP_IMAGE" ]]; then
    echo "- On failure, would rollback with: EQMD_IMAGE=$PREVIEW_BACKUP_IMAGE docker compose ${COMPOSE_OPTS[*]} up -d --no-build $APP_SERVICE"
  else
    echo "- On failure, rollback image may be unavailable (no current container image detected in preview)"
  fi

  print_status "Dry-run completed successfully"
  exit 0
fi

print_step "Preparing backup"
mkdir -p "$UPGRADE_BACKUP_DIR"
print_status "Backup directory: $UPGRADE_BACKUP_DIR"

if [[ -n "$SELECTED_ENV_FILE" ]]; then
  cp "$SELECTED_ENV_FILE" "$UPGRADE_BACKUP_DIR/env_snapshot_${TIMESTAMP}.env"
  print_status "Environment snapshot saved"
fi

# Image backup from running container (if any)
CURRENT_CONTAINER_ID="$(compose_cmd ps -q "$APP_SERVICE" | head -1 || true)"
CURRENT_IMAGE=""
BACKUP_IMAGE=""

if [[ -n "$CURRENT_CONTAINER_ID" ]]; then
  CURRENT_IMAGE="$(docker inspect "$CURRENT_CONTAINER_ID" --format '{{.Config.Image}}' 2>/dev/null || true)"
fi

if [[ -n "$CURRENT_IMAGE" ]]; then
  BACKUP_IMAGE="eqmd-rootless-backup:${TIMESTAMP}"
  docker tag "$CURRENT_IMAGE" "$BACKUP_IMAGE"
  print_status "Current image backed up as: $BACKUP_IMAGE"
  echo "$CURRENT_IMAGE" >"$UPGRADE_BACKUP_DIR/current_image.txt"
  echo "$BACKUP_IMAGE" >"$UPGRADE_BACKUP_DIR/backup_image.txt"
else
  print_warning "No running '$APP_SERVICE' container found; image backup skipped"
fi

# Database backup (recommended)
DB_BACKUP_FILE=""
if [[ "$SKIP_DB_BACKUP" == "1" ]]; then
  print_warning "Database backup skipped (SKIP_DB_BACKUP=1)"
elif [[ "$DB_SERVICE_EXISTS" == "true" ]]; then
  print_info "Ensuring database service is running..."
  compose_cmd up -d "$DB_SERVICE"

  DB_BACKUP_FILE="$UPGRADE_BACKUP_DIR/postgres_${POSTGRES_DB}_${TIMESTAMP}.dump"
  print_info "Creating PostgreSQL backup: $DB_BACKUP_FILE"

  if compose_cmd exec -T "$DB_SERVICE" sh -c "pg_dump -U \"${POSTGRES_USER}\" -d \"${POSTGRES_DB}\" -Fc" >"$DB_BACKUP_FILE"; then
    print_status "Database backup completed"
  else
    print_error "Database backup failed"
    exit 1
  fi
else
  print_warning "Database service '$DB_SERVICE' not found; DB backup skipped"
fi

print_step "Fetching updated application image"
IMAGE_UPDATED=false
IMAGE_BUILT=false

if [[ "$FORCE_BUILD" == "1" ]]; then
  print_info "FORCE_BUILD=1 -> building image locally"
  compose_cmd build "$APP_SERVICE"
  IMAGE_BUILT=true
else
  NEW_IMAGE="${EQMD_IMAGE:-}"
  if [[ -n "$NEW_IMAGE" ]]; then
    print_info "Pulling image: $NEW_IMAGE"
    if docker pull "$NEW_IMAGE"; then
      export EQMD_IMAGE="$NEW_IMAGE"
      IMAGE_UPDATED=true
      print_status "Image pulled successfully"
    else
      print_warning "Image pull failed; building locally"
      compose_cmd build "$APP_SERVICE"
      IMAGE_BUILT=true
      print_status "Local build completed"
    fi
  else
    print_info "EQMD_IMAGE not set; trying compose pull for service '$APP_SERVICE'"
    if compose_cmd pull "$APP_SERVICE"; then
      IMAGE_UPDATED=true
      print_status "Service image pulled via compose"
    else
      print_warning "Compose pull failed; building locally"
      compose_cmd build "$APP_SERVICE"
      IMAGE_BUILT=true
      print_status "Local build completed"
    fi
  fi
fi

print_step "Deploying updated service"
compose_cmd up -d "$APP_SERVICE"

APP_CONTAINER_ID="$(compose_cmd ps -q "$APP_SERVICE" | head -1 || true)"
if [[ -z "$APP_CONTAINER_ID" ]]; then
  print_error "Container for '$APP_SERVICE' did not start"
  rollback_to_backup_image || true
  exit 1
fi
print_status "Container started: $APP_CONTAINER_ID"

print_step "Running post-deploy Django commands"
compose_cmd exec -T "$APP_SERVICE" python manage.py migrate --noinput
print_status "Database migrations completed"

if [[ "$SKIP_SITE_CONFIGURE" != "1" ]]; then
  if compose_cmd exec -T "$APP_SERVICE" python manage.py help 2>/dev/null | grep -q "configure_django_site"; then
    compose_cmd exec -T "$APP_SERVICE" python manage.py configure_django_site
    print_status "Django Site Framework configured"
  else
    print_info "configure_django_site command not found; skipping"
  fi
else
  print_warning "Skipping configure_django_site (SKIP_SITE_CONFIGURE=1)"
fi

if [[ "$SKIP_COLLECTSTATIC" != "1" ]]; then
  compose_cmd exec -T "$APP_SERVICE" python manage.py collectstatic --noinput
  print_status "Static files collected"
else
  print_warning "Skipping collectstatic (SKIP_COLLECTSTATIC=1)"
fi

print_step "Health check"
print_info "Checking: $HEALTH_URL"
if wait_for_health "$HEALTH_URL" "$HEALTH_TIMEOUT_SECONDS" "$HEALTH_INTERVAL_SECONDS"; then
  print_status "Health check passed"
else
  print_error "Health check failed"
  if rollback_to_backup_image; then
    print_warning "Upgrade failed, but rollback restored the previous version"
    echo ""
    echo "Rollback details:"
    echo "- Backup image: ${BACKUP_IMAGE:-none}"
    if [[ -n "$DB_BACKUP_FILE" ]]; then
      echo "- Database backup: $DB_BACKUP_FILE"
    fi
    exit 1
  fi
  exit 1
fi

print_step "Upgrade completed"
echo -e "${GREEN}🎉 Rootless upgrade completed successfully!${NC}"

echo ""
echo "Summary:"
if [[ "$IMAGE_UPDATED" == "true" ]]; then
  echo "- Image update: pulled from registry"
elif [[ "$IMAGE_BUILT" == "true" ]]; then
  echo "- Image update: built locally"
else
  echo "- Image update: unchanged"
fi

echo "- App service: $APP_SERVICE"
echo "- Health URL: $HEALTH_URL"
echo "- Backup directory: $UPGRADE_BACKUP_DIR"
if [[ -n "$BACKUP_IMAGE" ]]; then
  echo "- Rollback image tag: $BACKUP_IMAGE"
fi
if [[ -n "$DB_BACKUP_FILE" ]]; then
  echo "- Database backup: $DB_BACKUP_FILE"
fi

echo ""
echo "Useful commands:"
echo "- Logs: docker compose ${COMPOSE_OPTS[*]} logs -f $APP_SERVICE"
if [[ -n "$BACKUP_IMAGE" ]]; then
  echo "- Manual rollback: EQMD_IMAGE=$BACKUP_IMAGE docker compose ${COMPOSE_OPTS[*]} up -d --no-build $APP_SERVICE"
fi
if [[ -n "$DB_BACKUP_FILE" ]]; then
  echo "- DB restore (manual): cat $DB_BACKUP_FILE | docker compose ${COMPOSE_OPTS[*]} exec -T $DB_SERVICE pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists"
fi
