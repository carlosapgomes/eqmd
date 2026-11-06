"""Create the disposable users and patient the verify-eqmd journeys need.

Runs INSIDE the dev container through ``manage.py shell`` (Django already
configured, database reachable). Writes one machine-readable line to stdout:

    EQMD_VERIFY_SCAFFOLD={"student": {...}, "doctor": {...}, "patient": {...}}

Constraints:
- Creates only disposable scaffolding: two users whose e-mail addresses use the
  reserved ``.invalid`` TLD and one patient named ``VERIFICACAO Skill <run-id>``.
- Idempotent for the users (get_or_create keyed by e-mail), fresh patient per
  run so reruns never share clinical rows.
- Never adopts an existing patient. If the run's exact name is already taken,
  this script creates nothing and exits non-zero: a pre-existing row was not
  created by this invocation, and ``cleanup.py`` deletes by ownership
  certificate, never by name.
- The created row's ``id``, ``created_by`` and ``created_at`` are part of the
  payload; that triple is the run's ownership certificate, the only thing
  ``cleanup.py`` is allowed to delete.
- Never touches operator data; it only creates.
"""

import json
import os
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from allauth.account.models import EmailAddress
from apps.patients.models import Patient

RUN_ID = os.environ.get("EQMD_VERIFY_RUN_ID", "manual")
PASSWORD = os.environ.get("EQMD_VERIFY_PASSWORD", "Verify!2026#eqmd")
STUDENT_EMAIL = os.environ.get(
    "EQMD_VERIFY_STUDENT_EMAIL", "verify.student@eqmd-verify.invalid"
)
DOCTOR_EMAIL = os.environ.get(
    "EQMD_VERIFY_DOCTOR_EMAIL", "verify.doctor@eqmd-verify.invalid"
)
PATIENT_NAME = os.environ.get("EQMD_VERIFY_PATIENT_NAME", f"VERIFICACAO Skill {RUN_ID}")

# apps.accounts.models.EqmdCustomUser profession codes.
STUDENT = 4
MEDICAL_DOCTOR = 0

User = get_user_model()


def ensure_user(email, profession_type, group_name):
    """Create or refresh one disposable account and make it login-ready."""
    user, _created = User.objects.get_or_create(
        username=email, defaults={"email": email}
    )
    user.email = email
    user.profession_type = profession_type
    user.is_active = True
    # Both flags default to True/False in ways that redirect the login to
    # /password-change-required/ or /accept-terms/, which would hide every
    # journey behind a gate.
    user.password_change_required = False
    user.terms_accepted = True
    user.terms_accepted_at = timezone.now()
    user.account_status = "active"
    user.access_expires_at = None
    user.set_password(PASSWORD)
    user.save()

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.set([group])

    address, _ = EmailAddress.objects.get_or_create(
        user=user, email=email, defaults={"verified": True, "primary": True}
    )
    if not address.verified or not address.primary:
        EmailAddress.objects.filter(user=user).update(primary=False)
        address.verified = True
        address.primary = True
        address.save()

    return user


def refuse_if_patient_name_taken(name):
    """Refuse to adopt a pre-existing row: an equal name is not ownership."""
    existing = list(
        Patient.all_objects.filter(name=name)
        .order_by("created_at")
        .values_list("id", "created_by__username", "created_at")
    )
    if not existing:
        return
    rows = ", ".join(
        f"{pk} (created_by={creator}, created_at={created_at.isoformat()})"
        for pk, creator, created_at in existing
    )
    raise SystemExit(
        f"EQMD_VERIFY_SCAFFOLD_REFUSED: {len(existing)} patient(s) are already "
        f"named {name!r}: {rows}. This invocation did not create them, and "
        f"cleanup deletes by ownership certificate, so setup created nothing. "
        f"Stale rows: re-run cleanup under the OLD run id first "
        f"(EQMD_VERIFY_RUN_ID=<old-run-id> npm run cleanup), or pick a fresh "
        f"EQMD_VERIFY_RUN_ID / EQMD_VERIFY_PATIENT_NAME."
    )


def create_patient(name, creator):
    """Create the disposable patient row this run writes against."""
    # Patient.save() runs full_clean(), which requires both audit FKs.
    return Patient.objects.create(
        name=name,
        birthday=date(1980, 1, 1),
        gender=Patient.GenderChoices.NOT_INFORMED,
        status=Patient.Status.OUTPATIENT,
        created_by=creator,
        updated_by=creator,
    )


# Checked before any insert: a refused setup must leave the database as it was.
refuse_if_patient_name_taken(PATIENT_NAME)

student = ensure_user(STUDENT_EMAIL, STUDENT, "Students")
doctor = ensure_user(DOCTOR_EMAIL, MEDICAL_DOCTOR, "Medical Doctors")
patient = create_patient(PATIENT_NAME, doctor)

payload = {
    "run_id": RUN_ID,
    "password": PASSWORD,
    "student": {
        "id": student.pk,
        "email": student.email,
        "profession_type": student.profession_type,
        "can_add_event": student.has_perm("events.add_event"),
        "can_change_event": student.has_perm("events.change_event"),
        "can_delete_event": student.has_perm("events.delete_event"),
    },
    "doctor": {
        "id": doctor.pk,
        "email": doctor.email,
        "profession_type": doctor.profession_type,
        "can_add_event": doctor.has_perm("events.add_event"),
        "can_change_event": doctor.has_perm("events.change_event"),
    },
    "patient": {
        # Ownership certificate: cleanup.py deletes by this triple or not at all.
        "id": str(patient.pk),
        "name": patient.name,
        "created_by": patient.created_by.username,
        "created_at": patient.created_at.isoformat(),
        "timeline_path": f"/patients/{patient.pk}/timeline/",
        "simplenote_create_path": f"/simplenotes/patient/{patient.pk}/create/",
        "discharge_create_path": f"/dischargereports/patient/{patient.pk}/create/",
        "apac_path": f"/pdf-forms/apac/{patient.pk}/",
        "existing_events": patient.events.count() if hasattr(patient, "events") else None,
    },
}

print("EQMD_VERIFY_SCAFFOLD=" + json.dumps(payload))
