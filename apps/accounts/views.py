import json
import uuid

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, RedirectView, UpdateView

from .forms import UserProfileForm
from .models import UserProfile
from .services import team_membership


@login_required
def profile_view(request, public_id):
    profile = get_object_or_404(UserProfile, public_id=public_id)
    context = {
        "profile": profile,
        # Include user properties via profile properties
        "is_owner": request.user == profile.user,
    }
    return render(request, "accounts/profile.html", context)


class ProfileDetailView(DetailView):
    model = UserProfile
    template_name = "accounts/profile.html"
    context_object_name = "profile"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_owner"] = self.request.user == self.object.user
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/profile_update.html"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_success_url(self):
        return reverse_lazy(
            "apps.accounts:profile", kwargs={"public_id": self.object.public_id}
        )

    def get_queryset(self):
        # Ensure users can only edit their own profile
        return UserProfile.objects.filter(user=self.request.user)


class ProfileRedirectView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy(
            "apps.accounts:profile",
            kwargs={"public_id": self.request.user.profile.public_id},
        )


@login_required
@require_http_methods(["POST"])
def change_specialty_api(request):
    """
    API endpoint for changing user's current specialty.

    Expects JSON body with specialty_id.
    Validates that specialty is assigned to user and is active.
    """
    # Parse specialty_id from JSON or form data
    if 'application/json' in request.content_type:
        try:
            body = json.loads(request.body)
            specialty_id = body.get('specialty_id')
        except json.JSONDecodeError:
            return JsonResponse(
                {'success': False, 'error': 'Invalid JSON'},
                status=400
            )
    else:
        specialty_id = request.POST.get('specialty_id')

    # Validate UUID format
    try:
        specialty_id = uuid.UUID(str(specialty_id))
    except (ValueError, AttributeError, TypeError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid specialty ID'},
            status=400
        )

    # Verify user has an active membership in an active specialty
    try:
        specialty = team_membership.get_eligible_specialty(
            request.user, specialty_id
        )
    except ValidationError:
        return JsonResponse(
            {'success': False, 'error': 'Specialty not assigned to user'},
            status=403
        )

    # Update current specialty through the request-time eligibility service
    team_membership.set_current_specialty(
        profile=request.user.profile, specialty=specialty
    )

    return JsonResponse({'success': True})
