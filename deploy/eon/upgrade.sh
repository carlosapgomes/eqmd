#!/usr/bin/env bash
# EQMD eon production upgrade (digest-pinned stack).
# Usage: EQMD_APP_DIR=/srv/apps/eqmd ./upgrade.sh <vX.Y.Z | ghcr.io/...:vX.Y.Z | sha256:...> [--yes]
# Tags are RESOLVED to a digest up front (shown at the gate); the compose
# always receives the immutable digest, never the mutable tag.
set -euo pipefail
umask 077

# Default: the directory where this script is installed (the deployment
# dir). Override with EQMD_APP_DIR if running it from elsewhere.
APP_DIR="${EQMD_APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
NEW_IMAGE="${1:-}"
ASSUME_YES="${2:-}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

fail() { echo "ERRO: $*" >&2; exit 1; }
gate() {
  [ "$ASSUME_YES" = "--yes" ] && return 0
  read -r -p "$1 [s/N] " ans
  [[ "$ans" =~ ^[sS]$ ]]
}

[ -n "$APP_DIR" ] || fail "diretorio de implantacao invalido"
[ -n "$NEW_IMAGE" ] || fail "uso: upgrade.sh <vX.Y.Z|sha256:...> [--yes]"

IMAGE_REPO="ghcr.io/carlosapgomes/eqmd"
case "$NEW_IMAGE" in
  sha256:[a-f0-9]{64}) : ;;
  "$IMAGE_REPO"@sha256:[a-f0-9]{64})
    NEW_IMAGE="${NEW_IMAGE##*@}" ;;
  "$IMAGE_REPO":*)
    NEW_IMAGE="${NEW_IMAGE##*:}" ;;
  [A-Za-z0-9][A-Za-z0-9._-]*) : ;;
  *) fail "referencia invalida: use vX.Y.Z, $IMAGE_REPO:vX.Y.Z ou sha256:<digest>" ;;
esac

case "$NEW_IMAGE" in
  sha256:*) NEW_DIGEST="$NEW_IMAGE"; TAG_INPUT="" ;;
  *)
    TAG_INPUT="$NEW_IMAGE"
    echo "== resolvendo tag $TAG_INPUT -> digest =="
    NEW_DIGEST="$(docker manifest inspect -v "$IMAGE_REPO:$TAG_INPUT" 2>/dev/null \
      | grep -m1 '"digest"' | sed 's/.*"digest": "\([^"]*\)".*/\1/')"
    [[ "$NEW_DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]] \
      || fail "nao consegui resolver $IMAGE_REPO:$TAG_INPUT para um digest (tag existe?)"
    echo "   $IMAGE_REPO:$TAG_INPUT -> $NEW_DIGEST" ;;
esac
[ "$APP_DIR" = "/" ] && fail "EQMD_APP_DIR invalido"

COMPOSE="$APP_DIR/docker-compose.eon.yml"
ENV_FILE="$APP_DIR/env.eon"
EV="$APP_DIR/staging/upgrades/$TS"

cd "$APP_DIR"
[ -f "$COMPOSE" ] && [ -f "$ENV_FILE" ] || fail "compose/env ausentes em $APP_DIR"

# Exclusive lock: one upgrade at a time per deployment.
exec 9>/run/lock/eqmd-upgrade.lock
flock -n 9 || fail "outra execucao de upgrade em andamento"

dc() { docker compose -f "$COMPOSE" --env-file "$ENV_FILE" "$@"; }

# All app-digest references must be identical before we touch anything.
mapfile -t REFS < <(grep -o 'ghcr.io/carlosapgomes/eqmd@sha256:[a-f0-9]*' "$COMPOSE" | sed 's/.*@//')
[ "${#REFS[@]}" -ge 2 ] || fail "esperado >=2 referencias de digest da app (eqmd/init/migrate)"
for r in "${REFS[@]}"; do
  [ "$r" = "${REFS[0]}" ] || fail "digests divergentes no compose (${REFS[0]} vs $r) - resolver manualmente antes"
done
OLD_DIGEST="${REFS[0]}"
N_BEFORE="${#REFS[@]}"

mkdir -p "$EV" && chmod 700 "$EV"

rollback_help() {
  cat <<EOF
ROLLBACK (digest atual registrado: $OLD_DIGEST):
  sed -i 's|eqmd@[^ "]*|eqmd@$OLD_DIGEST|g' $COMPOSE
  docker compose -f $COMPOSE --env-file $ENV_FILE up -d
  docker compose -f $COMPOSE --env-file $ENV_FILE --profile ops run --rm init
  # (init recompoe os estaticos da versao anterior; valide login e /health/)
  # schema e forward-only: restaure backup apenas com procedimento dedicado
  # (cutover/rollback.md); backup desta execucao: $EV
EOF
}
trap 'echo; echo "== FALHA no meio do upgrade =="; rollback_help' ERR

echo "== upgrade $TS =="
[ -n "$TAG_INPUT" ] && echo "   tag    : $IMAGE_REPO:$TAG_INPUT"
echo "   atual : $OLD_DIGEST ($N_BEFORE servicos)"
echo "   novo  : $NEW_DIGEST"

echo "== 0. preflight =="
dc ps >"$EV/ps-before.txt" 2>&1 || true
docker images --digests >"$EV/images-before.txt" 2>&1 || true
df -h "$APP_DIR" | tee "$EV/df.txt"
cp "$COMPOSE" "$EV/compose-before.yml"

echo "== 1. backup fresco (obrigatorio) =="
dc exec -T postgres pg_dump -U eqmd_migrator -d eqmd_db -Fc \
  >"$EV/db-pre-upgrade.dump" || fail "pg_dump falhou - NAO prosseguir"
docker run --rm -v eqmd_media:/media:ro --entrypoint tar \
  "ghcr.io/carlosapgomes/eqmd@$OLD_DIGEST" -C /media -czf - . \
  >"$EV/media-pre-upgrade.tgz" || fail "export de midia falhou"
sha256sum "$EV/db-pre-upgrade.dump" "$EV/media-pre-upgrade.tgz" \
  | tee "$EV/backup.sha256"
[ -s "$EV/db-pre-upgrade.dump" ] || fail "dump vazio - NAO prosseguir"
[ -s "$EV/media-pre-upgrade.tgz" ] || fail "midia vazia - NAO prosseguir"
[ -n "$TAG_INPUT" ] && echo "$IMAGE_REPO:$TAG_INPUT $NEW_DIGEST" >"$EV/tag-resolved.txt"
echo "   backup ok: $(du -h "$EV/db-pre-upgrade.dump" | cut -f1) db + $(du -h "$EV/media-pre-upgrade.tgz" | cut -f1) midia"

gate "== 2. aplicar novo digest no compose?" || fail "abortado"
sed -i "s|ghcr.io/carlosapgomes/eqmd@$OLD_DIGEST|ghcr.io/carlosapgomes/eqmd@$NEW_DIGEST|g" "$COMPOSE"
AFTER="$(grep -c "ghcr.io/carlosapgomes/eqmd@$NEW_DIGEST" "$COMPOSE" || true)"
LEFT="$(grep -c "ghcr.io/carlosapgomes/eqmd@$OLD_DIGEST" "$COMPOSE" || true)"
[ "$AFTER" = "$N_BEFORE" ] && [ "$LEFT" = "0" ] \
  || fail "sed nao cobriu todos os servicos (novos=$AFTER/$N_BEFORE, restantes=$LEFT) - restaurar $EV/compose-before.yml"
cp "$COMPOSE" "$EV/compose-new.yml"

echo "== 3. pull =="
dc pull 2>&1 | tee "$EV/pull.log"
docker image inspect "ghcr.io/carlosapgomes/eqmd@$NEW_DIGEST" \
  --format 'puxado: {{index .RepoDigests 0}}' | tee -a "$EV/pull.log"

echo "== 4. up -d (recria servicos alterados) =="
dc up -d 2>&1 | tee "$EV/up.log"

echo "== 5. estaticos =="
dc --profile ops run --rm init >"$EV/init.log" 2>&1 || fail "init/collectstatic falhou"

echo "== 6. migrate (gated) =="
dc --profile ops run --rm migrate sh -c \
  'python manage.py migrate --plan' | tee "$EV/migrate-plan.txt"
if grep -q "No planned migration operations" "$EV/migrate-plan.txt"; then
  echo "   sem migrations pendentes"
else
  gate "   aplicar migrations AGORA?" || fail "abortado antes do migrate"
  dc --profile ops run --rm migrate | tee "$EV/migrate-run.log"
fi

echo "== 7. health gate (estrito) =="
HEALTHY=0
# eqmd healthcheck: interval 30s, retries 3, start_period 60s (medido no
# deploy) -> janela de espera 180s cobre start_period + retries + margem.
for i in $(seq 1 45); do
  ST="$(docker inspect --format '{{.State.Health.Status}}' \
    "$(docker compose -f "$COMPOSE" --env-file "$ENV_FILE" ps -q eqmd)" 2>/dev/null || true)"
  echo "   tentativa $i: health=$ST"
  if [ "$ST" = "healthy" ]; then HEALTHY=1; break; fi
  sleep 4
done
[ "$HEALTHY" = "1" ] || { echo "container nao ficou healthy apos 45 tentativas (180s)" >&2; false; }
dc exec -T eqmd python -c \
  "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health/').read().decode())" \
  | tee "$EV/health.txt" | grep -q OK || fail "health nao OK"

trap - ERR
dc ps >"$EV/ps-after.txt" 2>&1
echo "== UPGRADE OK — evidencias em $EV =="
rollback_help
