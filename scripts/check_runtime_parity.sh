#!/usr/bin/env bash
# Runtime parity gate (ADR-0001).
#
# Proves that the Django minor line resolved in the committed uv.lock matches
# the Django version installed in the running environment. When they diverge
# (for example, an image built without the lock), the gate fails explicitly
# instead of silently running an unsupported runtime.
#
# The script never installs or mutates packages; a mismatch is fixed by
# rebuilding the image from the committed lock.
set -euo pipefail

locked_django="$(awk '/^name = "django"$/{found=1} found && /^version = /{print $3; exit}' uv.lock | tr -d '"')"
installed_django="$(python -c 'import django; print(django.get_version())')"

minor_line() {
    printf '%s' "${1}" | cut -d. -f1,2
}

echo "uv.lock Django:    ${locked_django}"
echo "Installed Django:  ${installed_django}"

if [ -z "${locked_django}" ]; then
    echo "ERROR: no 'django' entry found in uv.lock" >&2
    exit 2
fi

if [ "$(minor_line "${locked_django}")" != "$(minor_line "${installed_django}")" ]; then
    echo "ERROR: installed Django (${installed_django}) is outside the locked minor line (${locked_django})." >&2
    echo "Rebuild the image from the committed lock before running quality gates." >&2
    exit 1
fi

echo "OK: installed Django matches the locked minor line."
