from django.urls import path
from . import views

app_name = "apps.dailynotes"

urlpatterns = [
    # DailyNote CRUD URLs
    path("", views.DailyNoteListView.as_view(), name="dailynote_list"),
    path("<uuid:pk>/", views.DailyNoteDetailView.as_view(), name="dailynote_detail"),
    path("create/", views.DailyNoteCreateView.as_view(), name="dailynote_create"),
    path(
        "<uuid:pk>/update/",
        views.DailyNoteUpdateView.as_view(),
        name="dailynote_update",
    ),
    path(
        "<uuid:pk>/delete/",
        views.DailyNoteDeleteView.as_view(),
        name="dailynote_delete",
    ),
    # Patient-specific DailyNote URLs
    path(
        "patient/<uuid:patient_pk>/",
        views.PatientDailyNoteListView.as_view(),
        name="patient_dailynote_list",
    ),
    path(
        "patient/<uuid:patient_pk>/create/",
        views.PatientDailyNoteCreateView.as_view(),
        name="patient_dailynote_create",
    ),
    path(
        "patient/<uuid:patient_pk>/export/",
        views.PatientDailyNoteExportView.as_view(),
        name="patient_dailynote_export",
    ),
    # Print URLs
    path(
        "<uuid:pk>/print/", views.DailyNotePrintView.as_view(), name="dailynote_print"
    ),
]
