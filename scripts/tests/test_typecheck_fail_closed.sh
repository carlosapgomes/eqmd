#!/usr/bin/env bash
# Fail-closed regression test for quality scripts (ADR-0001).
#
# Simulates a development container where a required tool is absent using a
# fake `docker` executable on PATH. Proves each quality script:
#   1. exits nonzero when a required tool is missing;
#   2. prints explicit rebuild/remediation guidance;
#   3. never attempts to install packages or mutate dependencies;
#   4. never elevates privileges (no `--user root`).
#
# Scenarios covered (R1 + R2):
#   1. typecheck.sh with mypy missing;
#   2. install-dev-deps.sh with mypy missing, ruff available;
#   3. install-dev-deps.sh with ruff missing, mypy available.
#
# The live container is never touched: the fake docker shim intercepts
# every invocation and records it to a log file.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_TMP="$(mktemp -d)"
trap 'rm -rf "${TEST_TMP}"' EXIT

FAKE_DOCKER="${TEST_TMP}/docker"
FAKE_LOG="${TEST_TMP}/docker-calls.log"

# Forbidden dependency-mutation / elevation commands. Every quality script
# must avoid all of these at runtime (fail-closed contract, ADR-0001).
FORBIDDEN_PATTERNS=(
  "uv pip install"
  "pip install"
  "python[^ ]* -m pip .*install"
  "uv sync"
  "uv add"
  "--user root"
)

cat >"${FAKE_DOCKER}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${FAKE_DOCKER_LOG:?}"
case "$*" in
  *"command -v ${FAKE_MISSING_TOOL:?}"*) exit 1 ;;
  *) exit 0 ;;
esac
EOF
chmod +x "${FAKE_DOCKER}"

export FAKE_DOCKER_LOG="${FAKE_LOG}"

fail() {
  echo "FAIL: $*" >&2
  echo "--- script output ---" >&2
  echo "${output}" >&2
  echo "--- docker calls ---" >&2
  cat "${FAKE_LOG}" >&2
  exit 1
}

assert_no_mutation() {
  local haystack
  haystack="${output}"$'\n'"$(cat "${FAKE_LOG}")"
  local pattern
  for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if grep -Eq -- "${pattern}" <<<"${haystack}"; then
      fail "mutation/elevation attempt detected: ${pattern}"
    fi
  done
}

run_scenario() {
  local description="$1"
  local script="$2"
  local missing_tool="$3"
  local script_args=("${@:4}")

  : >"${FAKE_LOG}"
  export FAKE_MISSING_TOOL="${missing_tool}"

  set +e
  output="$(
    PATH="${TEST_TMP}:${PATH}" \
    EQMD_DOCKER_SERVICE=simulated-dev \
    "${REPO_ROOT}/${script}" "${script_args[@]}" 2>&1
  )"
  status=$?
  set -e

  [ "${status}" -ne 0 ] \
    || fail "${description}: expected nonzero exit, got 0"
  grep -q "command -v ${missing_tool}" "${FAKE_LOG}" \
    || fail "${description}: availability check for ${missing_tool} was not performed"
  grep -qi "rebuild" <<<"${output}" \
    || fail "${description}: missing rebuild/remediation guidance"
  grep -q "${missing_tool}" <<<"${output}" \
    || fail "${description}: expected missing tool not reported in output"
  assert_no_mutation

  echo "PASS: ${description}"
}

run_scenario \
  "typecheck.sh fails closed when mypy is absent (no install, no root, rebuild guidance)" \
  "scripts/typecheck.sh" "mypy" "apps/core/permissions"

run_scenario \
  "install-dev-deps.sh fails closed when mypy is missing and ruff is available" \
  "scripts/install-dev-deps.sh" "mypy"

run_scenario \
  "install-dev-deps.sh fails closed when ruff is missing and mypy is available" \
  "scripts/install-dev-deps.sh" "ruff"

echo "ALL PASS: 3/3 scenarios fail closed (no install, no root, rebuild guidance)."
