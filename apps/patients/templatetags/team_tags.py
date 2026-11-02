"""Template access to the current team leadership of a user.

Single purpose: the navigation entry for the leader team tag page must render
only for a user who currently leads an active team. Leadership itself stays in
``apps.accounts.services.team_membership``; this filter only exposes it to
templates and never decides authorization on its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import template

from apps.accounts.services import team_membership

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser, MedicalSpecialty

register = template.Library()


@register.filter
def led_teams(user: EqmdCustomUser | None) -> list[MedicalSpecialty]:
    """Return the active teams the user currently leads, in catalogue order.

    The result is memoised on the per-request user instance because the layout
    renders its navigation twice (desktop sidebar and mobile offcanvas); the
    next request builds a new user instance, so a revocation still applies
    immediately. ``is None`` keeps an empty list cached instead of re-querying.
    """
    if user is None or not user.is_authenticated:
        return []
    cached = getattr(user, "_led_teams", None)
    if cached is None:
        cached = team_membership.leader_specialties(user)
        user._led_teams = cached
    return cached
