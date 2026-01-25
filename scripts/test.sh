#!/usr/bin/env bash
set -euo pipefail

DOCKER_SERVICE="${EQMD_DOCKER_SERVICE:-eqmd_dev}"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.test_settings}"

args=()
if [[ "${EQMD_TEST_KEEPDB:-1}" == "1" ]]; then
  args+=("--keepdb")
fi
if [[ "${EQMD_TEST_NOINPUT:-1}" == "1" ]]; then
  args+=("--noinput")
fi

exec docker exec \
  -e DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}" \
  "${DOCKER_SERVICE}" \
  python manage.py test "${args[@]}" "$@"
