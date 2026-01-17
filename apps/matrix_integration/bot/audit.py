import json
import logging

from django.utils import timezone


logger = logging.getLogger("matrix.bot.audit")


def log_event(
    *,
    direction,
    user_id,
    matrix_user,
    room_id,
    action,
    message,
    results_count=None,
    selected_patient_id=None,
):
    entry = {
        "timestamp": timezone.now().isoformat(),
        "direction": direction,
        "user_id": user_id,
        "matrix_user": matrix_user,
        "room_id": room_id,
        "action": action,
        "message": message,
    }
    if results_count is not None:
        entry["results_count"] = results_count
    if selected_patient_id is not None:
        entry["selected_patient_id"] = selected_patient_id

    logger.info(json.dumps(entry, ensure_ascii=True))
