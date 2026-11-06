"""Remove the scaffolding ``scaffold.py`` created for THIS run, nothing else.

Runs INSIDE the dev container through ``manage.py shell``. Prints one
machine-readable line:

    EQMD_VERIFY_CLEANUP={"patients_deleted": 1, "events_deleted": 3, ...}

Scope rules enforced here:
- Deletes at most one patient, and only the row ``scaffold.py`` created for
  this run. It is selected by the id recorded in the run's ownership
  certificate (``scaffold.json`` -> ``EQMD_VERIFY_PATIENT_ID``) and re-verified
  before deletion: same id, same run name, and ``created_by`` is this run's
  scaffold account. Events are hard-deleted only for that verified patient id.
- Without a recorded id (recovery runs whose ``scaffold.json`` is gone) it
  falls back to an exact name match and accepts it only when exactly one row
  carries the run's name and its ``created_by`` is one of the two verify
  accounts. The fallback is same-namespace only: a row matching the run name
  that a verify account created is deletable by that run id.
- Everything else is refused with a non-zero exit and no deletion: a row whose
  id/name/creator does not match the certificate, or more than one row with the
  run's name. A missing row is reported as ``already_clean``.
- Deactivates only the two ``@eqmd-verify.invalid`` accounts and strips their
  password so they cannot log in again; the rows stay for audit. Those two
  e-mail addresses are fixed singletons every run reuses (scaffold.py is
  idempotent on the e-mail), so this half of the scope is run-independent.
- Refuses to touch anything else: no truncation, no "delete all drafts", no
  process killing. Patients left by other run ids are only counted, read-only.
"""

import json
import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.events.models import Event
from apps.patients.models import Patient

RUN_ID = os.environ.get("EQMD_VERIFY_RUN_ID", "manual")
PASSWORD = os.environ.get("EQMD_VERIFY_PASSWORD", "Verify!2026#eqmd")
PATIENT_PREFIX = "VERIFICACAO Skill"

# Same derivation as scaffold.py (which owns the created row), so the two can
# never disagree about which patient name belongs to this run. The harness
# passes EQMD_VERIFY_PATIENT_NAME explicitly for the same reason.
PATIENT_NAME = os.environ.get("EQMD_VERIFY_PATIENT_NAME", f"{PATIENT_PREFIX} {RUN_ID}")

# Ownership certificate scaffold.py wrote: the exact row id and the account that
# created it. Empty means "no certificate recorded" (recovery run), which
# forces the stricter name fallback below.
PATIENT_ID = (os.environ.get("EQMD_VERIFY_PATIENT_ID") or "").strip()
PATIENT_CREATED_BY = (os.environ.get("EQMD_VERIFY_PATIENT_CREATED_BY") or "").strip()

SCOPE_EMAILS = [
    os.environ.get(
        "EQMD_VERIFY_STUDENT_EMAIL", "verify.student@eqmd-verify.invalid"
    ),
    os.environ.get("EQMD_VERIFY_DOCTOR_EMAIL", "verify.doctor@eqmd-verify.invalid"),
]

User = get_user_model()


def name_matches():
    """Every patient carrying this run's name, oldest first."""
    return list(Patient.all_objects.filter(name=PATIENT_NAME).order_by("created_at"))


def creator_username(patient):
    return getattr(patient.created_by, "username", None)


def refuse(reason):
    """Delete nothing and fail loudly: this run's ownership of a row is unproven."""
    payload = {
        "run_id": RUN_ID,
        "patient_name": PATIENT_NAME,
        "recorded_patient_id": PATIENT_ID or None,
        "patient_id": None,
        "patient_created_by": None,
        "ownership": "refused",
        "refused": True,
        "already_clean": False,
        "reason": reason,
        "patients_deleted": 0,
        "events_deleted": 0,
        "patients": [],
        "users_deactivated": [],
        "run_patient_remaining": len(name_matches()),
        "verify_patients_outside_scope": Patient.all_objects.filter(
            name__startswith=PATIENT_PREFIX
        )
        .exclude(name=PATIENT_NAME)
        .count(),
    }
    print("EQMD_VERIFY_CLEANUP=" + json.dumps(payload))
    raise SystemExit(f"EQMD_VERIFY_CLEANUP_REFUSED: {reason} (nothing deleted)")


matches = name_matches()
if len(matches) > 1:
    refuse(
        f"{len(matches)} patients are named {PATIENT_NAME!r}; "
        "deleting an ambiguous match could destroy another run's data"
    )

target = None
ownership = "recorded-id"
already_clean = False

if PATIENT_ID:
    try:
        target = Patient.all_objects.filter(pk=PATIENT_ID).first()
    except (ValueError, ValidationError):
        refuse(f"recorded patient id {PATIENT_ID!r} is not a UUID")
    if target is None:
        already_clean = True
    else:
        if target.name != PATIENT_NAME:
            refuse(
                f"patient {PATIENT_ID} is named {target.name!r}, "
                f"not this run's {PATIENT_NAME!r}"
            )
        creator = creator_username(target)
        if creator not in SCOPE_EMAILS:
            refuse(
                f"patient {PATIENT_ID} was created by {creator!r}, "
                "not a verify account"
            )
        if PATIENT_CREATED_BY and creator != PATIENT_CREATED_BY:
            refuse(
                f"patient {PATIENT_ID} was created by {creator!r}, "
                f"not the recorded {PATIENT_CREATED_BY!r}"
            )
else:
    ownership = "name-fallback"
    if not matches:
        already_clean = True
    else:
        target = matches[0]
        creator = creator_username(target)
        if creator not in SCOPE_EMAILS:
            refuse(
                f"no recorded patient id and {PATIENT_NAME!r} was created by "
                f"{creator!r}, not a verify account"
            )

patient_summary = []
# Capture the verified identity before deleting: Django clears pk on delete.
verified_patient_id = str(target.pk) if target is not None else None
verified_creator = creator_username(target) if target is not None else None
events_deleted = 0
patients_deleted = 0

if target is not None:
    # Event.patient is on_delete=PROTECT, so the events must go first, and only
    # for the verified patient id.
    events = Event.all_objects.filter(patient_id=target.pk)
    event_ids = list(events.values_list("id", flat=True))
    for event in events:
        event.hard_delete()
    events_deleted = len(event_ids)
    patient_summary.append(
        {
            "id": verified_patient_id,
            "name": target.name,
            "created_by": verified_creator,
            "events": events_deleted,
        }
    )
    target.hard_delete()
    patients_deleted = 1

users_summary = []
for email in SCOPE_EMAILS:
    for user in User.objects.filter(username=email):
        user.is_active = False
        user.set_unusable_password()
        user.save()
        users_summary.append(
            {
                "username": user.username,
                "is_active": user.is_active,
                "password_still_valid": user.check_password(PASSWORD),
            }
        )

payload = {
    "run_id": RUN_ID,
    "patient_name": PATIENT_NAME,
    "recorded_patient_id": PATIENT_ID or None,
    "patient_id": verified_patient_id,
    "patient_created_by": verified_creator,
    "ownership": ownership,
    "refused": False,
    "already_clean": already_clean,
    "patients_deleted": patients_deleted,
    "events_deleted": events_deleted,
    "patients": patient_summary,
    "users_deactivated": users_summary,
    # This run's patient must be gone; other runs' patients are reported only.
    "run_patient_remaining": len(name_matches()),
    "verify_patients_outside_scope": Patient.all_objects.filter(
        name__startswith=PATIENT_PREFIX
    )
    .exclude(name=PATIENT_NAME)
    .count(),
}

print("EQMD_VERIFY_CLEANUP=" + json.dumps(payload))
