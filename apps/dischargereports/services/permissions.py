"""Collaborative discharge predicates for edit/delete actions.

One rule serves the model methods, the detail view helper and the patient
timeline bulk check (design D1/D2). Discharge reports share the generic
draft/owner rules delivered by the permission core (design D6/D7): drafts
allow the creator or any doctor/resident with patient access (no time limit);
finalized reports allow only their owner -- the finalizer when recorded, else
the creator -- within 24h of the finalization anchor.
"""

from apps.core.permissions import (
    can_access_patient,
    can_delete_event,
    can_edit_event,
)


def can_edit_discharge_report(user, report):
    """Return whether ``user`` may edit ``report``.

    Drafts: creator or any doctor/resident with patient access (collaborative
    draft workflow, no time limit; 0/1 are EqmdCustomUser
    MEDICAL_DOCTOR/RESIDENT). Finals: only the owner, inside the 24h window
    anchored at ``finalized_at`` (``created_at`` for legacy finals).
    """
    if not can_access_patient(user, report.patient):
        return False

    return can_edit_event(user, report)


def can_delete_discharge_report(user, report):
    """Return whether ``user`` may delete ``report``.

    Deletion rights follow the same state rules as editing: drafts belong to
    the creator or a doctor/resident, finals to the owner inside the window.
    """
    if not can_access_patient(user, report.patient):
        return False

    return can_delete_event(user, report)
