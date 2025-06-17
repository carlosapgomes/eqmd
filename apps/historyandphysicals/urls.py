from django.urls import path
from . import views

app_name = "apps.historyandphysicals"

urlpatterns = [
    # HistoryAndPhysical CRUD URLs
    # path("", views.HistoryAndPhysicalListView.as_view(), name="historyandphysical_list"),
    path("<uuid:pk>/", views.HistoryAndPhysicalDetailView.as_view(), name="historyandphysical_detail"),
    path(
        "<uuid:pk>/update/",
        views.HistoryAndPhysicalUpdateView.as_view(),
        name="historyandphysical_update",
    ),
    path(
        "<uuid:pk>/delete/",
        views.HistoryAndPhysicalDeleteView.as_view(),
        name="historyandphysical_delete",
    ),
    path(
        "<uuid:pk>/duplicate/",
        views.HistoryAndPhysicalDuplicateView.as_view(),
        name="historyandphysical_duplicate",
    ),
    # Patient-specific HistoryAndPhysical URLs
    # path(
    #     "patient/<uuid:patient_pk>/",
    #     views.PatientHistoryAndPhysicalListView.as_view(),
    #     name="patient_historyandphysical_list",
    # ),
    path(
        "patient/<uuid:patient_pk>/create/",
        views.PatientHistoryAndPhysicalCreateView.as_view(),
        name="patient_historyandphysical_create",
    ),
    path(
        "patient/<uuid:patient_pk>/export/",
        views.PatientHistoryAndPhysicalExportView.as_view(),
        name="patient_historyandphysical_export",
    ),
    # Print URLs
    path(
        "<uuid:pk>/print/", views.HistoryAndPhysicalPrintView.as_view(), name="historyandphysical_print"
    ),
]