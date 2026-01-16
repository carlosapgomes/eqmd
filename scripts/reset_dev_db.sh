#!/usr/bin/env bash
set -euo pipefail

# Reset dev databases and restore from a PostgreSQL dump.
#
# Usage:
#   ./scripts/reset_dev_db.sh /path/to/eqmd_production_backup.sql
#
# Notes:
# - This script DROPS and recreates the dev databases (eqmd_dev + matrix_db).
# - It expects to run from the repo root and will load .env for passwords.
# - If you don't need sudo for docker, run with: SUDO= ./scripts/reset_dev_db.sh ...
# - Requires: docker compose, psql inside the postgres container, and uv for matrix bootstrap.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" ]]; then
  echo "Usage: $0 /absolute/path/to/eqmd_backup.sql"
  exit 1
fi
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

SUDO="${SUDO:-sudo}"
COMPOSE_CMD=(docker compose)
if [[ -n "$SUDO" ]]; then
  COMPOSE_CMD=("$SUDO" "${COMPOSE_CMD[@]}")
fi

EQMD_DB="${DATABASE_NAME:-eqmd_dev}"
POSTGRES_USER="${POSTGRES_USER:-eqmd_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-eqmd_dev_password_123}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
MATRIX_DB="${MATRIX_DB:-matrix_db}"
MATRIX_DATABASE_PASSWORD="${MATRIX_DATABASE_PASSWORD:-}"

if [[ -z "$MATRIX_DATABASE_PASSWORD" ]]; then
  echo "MATRIX_DATABASE_PASSWORD is not set in .env"
  exit 1
fi

echo "Stopping app containers..."
"${COMPOSE_CMD[@]}" stop eqmd-dev matrix-synapse element-web

echo "Dropping databases..."
"${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$EQMD_DB\";"
"${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$MATRIX_DB\";"

echo "Creating $EQMD_DB..."
"${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$EQMD_DB\" OWNER \"$POSTGRES_USER\";"

echo "Restoring backup into $EQMD_DB..."
"${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "$EQMD_DB" -v ON_ERROR_STOP=1 <"$BACKUP_FILE"

echo "Starting eqmd-dev for migrations..."
"${COMPOSE_CMD[@]}" up -d eqmd-dev

# echo "Ensuring OIDC migrations are marked if tables already exist..."
# OIDC_TABLE_EXISTS="$("${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "$EQMD_DB" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='oidc_provider_client'")"
# OIDC_CONSENT_EXISTS="$("${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "$EQMD_DB" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='oidc_provider_userconsent'")"
# if [[ "$OIDC_TABLE_EXISTS" == "1" || "$OIDC_CONSENT_EXISTS" == "1" ]]; then
#   # Database already has oidc_provider tables from the dump; mark all migrations as applied.
#   "${COMPOSE_CMD[@]}" exec eqmd-dev python manage.py migrate oidc_provider --fake
# fi

# echo "Running migrations (with --fake-initial for restored schemas)..."
# "${COMPOSE_CMD[@]}" exec eqmd-dev python manage.py migrate --fake-initial

# echo "Verifying critical columns exist after migrations..."
# HAS_IS_DRAFT="$("${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "$EQMD_DB" -tAc "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='events_event' AND column_name='is_draft'")"
# if [[ "$HAS_IS_DRAFT" != "1" ]]; then
#   echo "Missing events_event.is_draft after migrations; attempting to realign events migrations..."
#   "${COMPOSE_CMD[@]}" exec eqmd-dev python manage.py migrate events 0001 --fake
#   "${COMPOSE_CMD[@]}" exec eqmd-dev python manage.py migrate events
#   HAS_IS_DRAFT="$("${COMPOSE_CMD[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "$EQMD_DB" -tAc "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='events_event' AND column_name='is_draft'")"
#   if [[ "$HAS_IS_DRAFT" != "1" ]]; then
#     echo "ERROR: events_event.is_draft is still missing. Check django_migrations state and schema."
#     exit 1
#   fi
# fi

echo "Bootstrapping Matrix database + user..."
POSTGRES_HOST="$POSTGRES_HOST" POSTGRES_PORT="$POSTGRES_PORT" \
  POSTGRES_USER="$POSTGRES_USER" POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  POSTGRES_DB="$EQMD_DB" MATRIX_DATABASE_PASSWORD="$MATRIX_DATABASE_PASSWORD" \
  uv run python scripts/bootstrap_matrix_db.py

echo "Starting app containers..."
"${COMPOSE_CMD[@]}" up -d matrix-synapse element-web

echo "Done."
