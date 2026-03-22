#!/usr/bin/env bash
set -euo pipefail

DOCKER_SERVICE="${EQMD_DOCKER_SERVICE:-eqmd_dev}"

exec docker exec --user root "${DOCKER_SERVICE}" sh -lc 'cd /app && uv pip install --system --group dev'
