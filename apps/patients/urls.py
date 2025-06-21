from django.urls import path
from . import views
from apps.events.views import PatientEventsTimelineView

app_name = "apps.patients"

urlpatterns = [
    # Patient URLs
    path("", views.PatientListView.as_view(), name="patient_list"),
    path("<uuid:pk>/", views.PatientDetailView.as_view(), name="patient_detail"),
    path("<uuid:patient_id>/timeline/", PatientEventsTimelineView.as_view(), name="patient_events_timeline"),
    path("create/", views.PatientCreateView.as_view(), name="patient_create"),
    path("<uuid:pk>/update/", views.PatientUpdateView.as_view(), name="patient_update"),
    path("<uuid:pk>/delete/", views.PatientDeleteView.as_view(), name="patient_delete"),
    # Hospital Record URLs
    path(
        "<uuid:patient_id>/records/create/",
        views.HospitalRecordCreateView.as_view(),
        name="hospital_record_create",
    ),
    path(
        "records/<uuid:pk>/update/",
        views.HospitalRecordUpdateView.as_view(),
        name="hospital_record_update",
    ),
    path(
        "records/<uuid:pk>/delete/",
        views.HospitalRecordDeleteView.as_view(),
        name="hospital_record_delete",
    ),
    # API URLs
    path(
        "api/<uuid:patient_id>/hospital-records/",
        views.PatientHospitalRecordsAPIView.as_view(),
        name="api_patient_hospital_records",
    ),
    path(
        "api/hospital-record/<uuid:hospital_id>/",
        views.HospitalRecordByHospitalAPIView.as_view(),
        name="api_hospital_record_by_hospital",
    ),
    # Tag URLs
    path("tags/", views.AllowedTagListView.as_view(), name="tag_list"),
    path("tags/create/", views.AllowedTagCreateView.as_view(), name="tag_create"),
    path(
        "tags/<int:pk>/update/", views.AllowedTagUpdateView.as_view(), name="tag_update"
    ),
    path(
        "tags/<int:pk>/delete/", views.AllowedTagDeleteView.as_view(), name="tag_delete"
    ),
]

