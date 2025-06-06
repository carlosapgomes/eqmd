from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, UpdateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import UserProfile
from .forms import UserProfileForm


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
