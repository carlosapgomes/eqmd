#!/usr/bin/env sh
set -eu

docker compose exec --user root eqmd-dev uv pip install --system --group dev
