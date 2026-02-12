#!/usr/bin/env bash
set -euo pipefail

DOCKER_SERVICE="${EQMD_DOCKER_SERVICE:-eqmd_dev}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/typecheck.sh <python-path> [<python-path> ...]

Examples:
  ./scripts/typecheck.sh apps/core/permissions
  ./scripts/typecheck.sh apps/simplenotes/apps.py
  ./scripts/typecheck.sh apps/core/permissions apps/patients/services
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

exec docker exec "${DOCKER_SERVICE}" mypy "$@"
