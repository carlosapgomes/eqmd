"""Synapse policy module to enforce room creation, invites, and E2EE rules."""

from __future__ import annotations

import re

try:
    from synapse.module_api import NOT_SPAM
except Exception:  # pragma: no cover - fallback for older Synapse imports
    NOT_SPAM = False


class EqmdPolicyModule:
    """Enforce server-side policy for room creation, invites, and encryption."""

    def __init__(self, config, api):
        self._admin_users = _parse_user_list(config.get("admin_users"))
        self._bot_user_id = (config.get("bot_user_id") or "").strip()
        self._admin_user_regex = _compile_regex(config.get("admin_user_regex"))
        self._block_room_creation = config.get("block_room_creation", True)
        self._block_invites = config.get("block_invites", True)
        self._block_encryption = config.get("block_encryption", True)

    def user_may_create_room(self, user_id, *args, **kwargs):
        if not self._block_room_creation:
            return True
        return self._is_privileged_user(user_id)

    def user_may_invite(self, inviter_userid, *args, **kwargs):
        if not self._block_invites:
            return True
        return self._is_privileged_user(inviter_userid)

    def user_may_send_event(self, event, *args, **kwargs):
        if self._block_encryption and _is_encryption_event(event):
            return False
        return True

    def check_event_for_spam(self, event):
        if self._block_encryption and _is_encryption_event(event):
            return True
        return NOT_SPAM

    def _is_privileged_user(self, user_id):
        if not user_id:
            return False
        if user_id == self._bot_user_id:
            return True
        if user_id in self._admin_users:
            return True
        if self._admin_user_regex and self._admin_user_regex.match(user_id):
            return True
        return False


def _parse_user_list(value: object) -> set[str]:
    if not value:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {item.strip() for item in str(value).split(",") if item.strip()}


def _compile_regex(value: object):
    if not value:
        return None
    try:
        return re.compile(str(value))
    except re.error:
        return None


def _is_encryption_event(event) -> bool:
    return getattr(event, "type", None) == "m.room.encryption"
