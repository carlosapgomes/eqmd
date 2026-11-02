"""Leader self-service views for the specialty team tag page.

Authorization is delegated to :mod:`apps.patients.services.tag_policy`; these
views only resolve the addressed team, shape the response and report feedback.
The team always comes from the explicit URL, so opening a team page never
changes the user's active specialty context.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.accounts.models import EqmdCustomUser, MedicalSpecialty
from apps.accounts.services import team_membership
from apps.patients.models import AllowedTag
from apps.patients.services import tag_catalogue, tag_policy, tag_projection

from .forms_team_tags import TeamTagForm


def _user_label(user: EqmdCustomUser | None) -> str:
    """Return the display label of a responsible leader, or a dash."""
    if user is None:
        return "—"
    return user.get_full_name() or user.username


def team_tag_rows(
    actor: EqmdCustomUser, specialty: MedicalSpecialty
) -> list[dict[str, Any]]:
    """Project the addressed team's readable restricted tags for the page.

    The read goes through the requester-aware S5 projection, then narrows to the
    addressed namespace, so no other team's restricted metadata can appear.
    Management rights reuse the shared policy predicate; the caller has already
    verified that the actor leads this team.
    """
    tags = (
        tag_projection.visible_catalogue(actor)
        .select_related("responsible_user")
        .filter(
            specialty=specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        .order_by("name")
    )
    state_labels = dict(AllowedTag.LifecycleState.choices)
    return [
        {
            "tag": tag,
            "state_label": state_labels[tag.lifecycle_state],
            "can_manage": tag_policy.is_manageable_by_leader(
                tag, leader_id=actor.pk
            ),
            "responsible_name": _user_label(tag.responsible_user),
        }
        for tag in tags
    ]


def _first_error_message(error: ValidationError) -> str:
    """Return the first human-readable service error message."""
    messages_list = error.messages
    return messages_list[0] if messages_list else "Não foi possível concluir a ação."


class LeaderTeamMixin(LoginRequiredMixin):
    """Resolve the addressed team and require current leadership of it."""

    specialty: MedicalSpecialty
    request: HttpRequest
    kwargs: dict[str, Any]

    @property
    def actor(self) -> EqmdCustomUser:
        """Return the authenticated account; login is already enforced."""
        return cast(EqmdCustomUser, self.request.user)

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        self.specialty = get_object_or_404(
            MedicalSpecialty, pk=kwargs["specialty_id"]
        )
        if request.user.is_authenticated:
            if not tag_policy.can_lead_team_catalogue(
                self.actor, self.specialty
            ):
                raise PermissionDenied(
                    "Team tag management requires current leadership of the team."
                )
            self.prepare()
        return super().dispatch(request, *args, **kwargs)

    def prepare(self) -> None:
        """Hook for views that also resolve a manageable catalogue row."""


class ManagedTeamTagMixin(LeaderTeamMixin):
    """Require the current responsible leader of a tag in the addressed team."""

    tag: AllowedTag

    def prepare(self) -> None:
        self.tag = get_object_or_404(
            AllowedTag.objects.select_related("specialty"),
            pk=self.kwargs["pk"],
            specialty=self.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        if not tag_policy.can_manage_tag(self.actor, self.tag):
            raise PermissionDenied(
                "Only the current responsible leader can manage this tag."
            )


class TeamTagListView(LeaderTeamMixin, TemplateView):
    """Show the leader's own team tags with their lifecycle state."""

    template_name = "patients/team_tags.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            specialty=self.specialty,
            team_tag_rows=team_tag_rows(self.actor, self.specialty),
            led_teams=team_membership.leader_specialties(self.actor),
        )
        return context


class TeamTagCreateView(LeaderTeamMixin, FormView):
    """Create a custom restricted tag in the addressed team."""

    template_name = "patients/team_tag_form.html"
    form_class = TeamTagForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["specialty"] = self.specialty
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            specialty=self.specialty,
            tag=None,
            form_title="Nova tag da equipe",
            submit_label="Criar tag",
        )
        return context

    def form_valid(self, form: TeamTagForm) -> HttpResponse:
        try:
            tag = tag_catalogue.create_team_tag(
                actor=self.actor,
                specialty=self.specialty,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f'Tag "{tag.name}" criada na equipe {self.specialty.abbreviation}.',
        )
        return redirect("patients:team_tags", specialty_id=self.specialty.pk)


class TeamTagEditView(ManagedTeamTagMixin, FormView):
    """Edit only the descriptive fields of a tag led by the current leader."""

    template_name = "patients/team_tag_form.html"
    form_class = TeamTagForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["specialty"] = self.specialty
        kwargs["exclude_pk"] = self.tag.pk
        return kwargs

    def get_initial(self) -> dict[str, Any]:
        return {
            "name": self.tag.name,
            "description": self.tag.description,
            "color": self.tag.color,
        }

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            specialty=self.specialty,
            tag=self.tag,
            form_title=f'Editar "{self.tag.name}"',
            submit_label="Salvar alterações",
        )
        return context

    def form_valid(self, form: TeamTagForm) -> HttpResponse:
        try:
            tag = tag_catalogue.edit_tag(
                actor=self.actor, tag=self.tag, **form.cleaned_data
            )
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        messages.success(self.request, f'Tag "{tag.name}" atualizada.')
        return redirect("patients:team_tags", specialty_id=self.specialty.pk)


class TeamTagDeactivateView(ManagedTeamTagMixin, View):
    """Inactivate the leader's own tag; associations and history remain."""

    http_method_names = ("post",)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            tag_catalogue.deactivate_tag(actor=self.actor, tag=self.tag)
        except ValidationError as error:
            messages.error(request, _first_error_message(error))
        else:
            messages.success(
                request,
                f'Tag "{self.tag.name}" desativada. Novas atribuições estão '
                "bloqueadas até a reativação.",
            )
        return redirect("patients:team_tags", specialty_id=self.specialty.pk)


class TeamTagReactivateView(ManagedTeamTagMixin, View):
    """Reactivate the leader's own inactive tag."""

    http_method_names = ("post",)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            tag_catalogue.reactivate_tag(actor=self.actor, tag=self.tag)
        except ValidationError as error:
            messages.error(request, _first_error_message(error))
        else:
            messages.success(
                request, f'Tag "{self.tag.name}" reativada e disponível.'
            )
        return redirect("patients:team_tags", specialty_id=self.specialty.pk)
