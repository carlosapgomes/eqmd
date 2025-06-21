from django.urls import path
from . import views

app_name = "apps.simplenotes"

urlpatterns = [
    # SimpleNote CRUD URLs
    path("<uuid:pk>/", views.SimpleNoteDetailView.as_view(), name="simplenote_detail"),
    path(
        "<uuid:pk>/update/",
        views.SimpleNoteUpdateView.as_view(),
        name="simplenote_update",
    ),
    path(
        "<uuid:pk>/delete/",
        views.SimpleNoteDeleteView.as_view(),
        name="simplenote_delete",
    ),
    path(
        "<uuid:pk>/duplicate/",
        views.SimpleNoteDuplicateView.as_view(),
        name="simplenote_duplicate",
    ),
    path(
        "patient/<uuid:patient_pk>/create/",
        views.PatientSimpleNoteCreateView.as_view(),
        name="patient_simplenote_create",
    ),
    # Print URLs
    path(
        "<uuid:pk>/print/", views.SimpleNotePrintView.as_view(), name="simplenote_print"
    ),
]