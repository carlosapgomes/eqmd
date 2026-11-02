"""Single collaborative predicate for discharge report edit/delete actions.

One rule serves the model methods, the detail view helper and the patient
timeline bulk check (design D1/D2). Semantics are the shipped collaborative
draft rules: drafts allow the creator, ``events.change_event`` holders or any
doctor/resident with patient access (no time limit); finalized reports follow
the standard event window for the creator or ``events.change_event`` holders.
"""

from apps.core.permissions import (
    can_access_patient,
    can_delete_event,
)


def can_edit_discharge_report(user, report):
    """Return whether ``user`` may edit ``report``.

    Drafts: creator, edit-permission holders, or any doctor/resident
    (collaborative draft workflow, no time limit). 0/1 are
    EqmdCustomUser MEDICAL_DOCTOR/RESIDENT. Finals keep the shipped rule:
    within the edit window, the creator or an ``events.change_event``
    holder.
    """
    if not can_access_patient(user, report.patient):
        return False

    if report.is_draft:
        if report.created_by == user or user.has_perm("events.change_event"):
            return True
        profession_type = getattr(user, "profession_type", None)
        return profession_type in (0, 1)

    return report.can_be_edited and (
        report.created_by == user or user.has_perm("events.change_event")
    )


def can_delete_discharge_report(user, report):
    """Return whether ``user`` may delete ``report``.

    Drafts: creator or delete-permission holders. Finals: the standard
    event rule or the delete-permission override.
    """
    if not can_access_patient(user, report.patient):
        return False

    if report.is_draft:
        return report.created_by == user or user.has_perm("events.delete_event")

    return can_delete_event(user, report) or user.has_perm("events.delete_event")
