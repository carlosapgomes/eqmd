"""Explicit tag preference mutations and the retained-settings overview (S8)."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms_tag_preferences import TagPreferenceSaveForm
from .services import tag_preferences


def _redirect_target(request) -> str:
    """Return a safe local destination after an explicit save."""
    candidate = request.POST.get("next", "")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("patients:patient_list")


@login_required
def tag_preferences_view(request):
    """Show the retained settings of every membership the user owns."""
    context = {
        "summaries": tag_preferences.preference_summaries(request.user),
    }
    return render(request, "accounts/tag_preferences.html", context)


@login_required
@require_POST
def save_tag_preference(request):
    """Persist the explicit selection for the still-current specialty only."""
    destination = _redirect_target(request)
    form = TagPreferenceSaveForm(request.POST)
    if not form.is_valid():
        messages.error(request, tag_preferences.SAVE_REJECTED_MESSAGE)
        return redirect(destination)
    try:
        tag_preferences.save_preference(
            actor=request.user,
            specialty_id=form.cleaned_data["specialty_id"],
            tag_ids=tuple(form.cleaned_data["tags"]),
            mode=form.selected_mode(),
        )
    except ValidationError:
        messages.error(request, tag_preferences.SAVE_REJECTED_MESSAGE)
        return redirect(destination)
    messages.success(request, tag_preferences.SAVE_SUCCESS_MESSAGE)
    return redirect(destination)
