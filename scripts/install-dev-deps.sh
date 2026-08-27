#!/usr/bin/env bash
# DEPRECATED diagnostic entry point (ADR-0001).
#
# Development tools (Ruff, Mypy) are provisioned at image build time from
# committed lock metadata. This script no longer installs packages: it
# diagnoses the development container and fails closed with rebuild
# guidance when a required tool is absent. It has no callers in the
# repository and is retained only for operator diagnostics.
set -euo pipefail

DOCKER_SERVICE="${EQMD_DOCKER_SERVICE:-eqmd_dev}"

missing=0

for tool in ruff mypy; do
  if docker exec "${DOCKER_SERVICE}" sh -lc "command -v ${tool} >/dev/null 2>&1"; then
    echo "[install-dev-deps] ${tool}: available in ${DOCKER_SERVICE}"
  else
    echo "[install-dev-deps] ${tool}: MISSING in ${DOCKER_SERVICE}" >&2
    missing=1
  fi
done

if [[ ${missing} -eq 1 ]]; then
  echo "[install-dev-deps] ERROR: required development tools are missing." >&2
  echo "[install-dev-deps] Rebuild the development image from the committed lock:" >&2
  echo "[install-dev-deps]   docker compose build eqmd-dev" >&2
  echo "[install-dev-deps] This script never installs packages (ADR-0001)." >&2
  exit 1
fi

echo "[install-dev-deps] OK: all development tools are provisioned. No installation performed."
