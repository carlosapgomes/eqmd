from django.urls import path

from . import views, views_tag_preferences

app_name = "apps.accounts"

urlpatterns = [
    path(
        "tag-preferences/",
        views_tag_preferences.tag_preferences_view,
        name="tag_preferences",
    ),
    path(
        "tag-preferences/save/",
        views_tag_preferences.save_tag_preference,
        name="tag_preference_save",
    ),
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
    path(
        "api/change-specialty/",
        views.change_specialty_api,
        name="change_specialty_api",
    ),
]
