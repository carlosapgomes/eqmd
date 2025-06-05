from django.urls import path
from . import views

app_name = "apps.accounts"

urlpatterns = [
    path("<uuid:public_id>/", views.profile_view, name="profile"),
    path(
        "<uuid:public_id>/detail/",
        views.ProfileDetailView.as_view(),
        name="profile_detail",
    ),
    path(
        "<uuid:public_id>/update/",
        views.ProfileUpdateView.as_view(),
        name="profile_update",
    ),
    path("redirect/", views.ProfileRedirectView.as_view(), name="profile_redirect"),
]
