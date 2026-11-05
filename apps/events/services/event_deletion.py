"""Generic event deletion: the method follows the record's history (design D7).

Deletion rights follow the *current* state and are enforced by the callers'
predicates (``can_delete_event``): drafts are deletable by their creator or by
any doctor/resident with patient access, definitive events only by the owner
inside the 24h window. This module owns the second half of the rule — the
*method* — for every event type:

- a draft that was never finalized loses its row (hard delete);
- anything ever finalized keeps the soft-delete path, because retained
  finalization metadata proves the content once entered the record.

Finalization metadata is retained on revert (design D5), so
``was_ever_finalized()`` answers the history question without a migration or a
history lookup. Media file cleanup is deliberately absent here; media types add
their own file handling on top of this helper.
"""


def delete_event_record(event, *, deleted_by=None, reason=""):
    """Delete ``event`` by the path its state and history require.

    Args:
        event: The event instance to delete.
        deleted_by: The acting user recorded on the soft-delete path.
        reason: Optional soft-delete reason.

    Returns:
        bool: True when the row was hard-deleted, False when it was soft-deleted.
    """
    if event.is_draft and not event.was_ever_finalized():
        event.hard_delete()
        return True

    event.delete(deleted_by=deleted_by, reason=reason)
    return False
