from django.urls import path
from . import views
from apps.events.views import PatientEventsTimelineView

app_name = "apps.patients"

urlpatterns = [
    # Patient URLs
    path("", views.PatientListView.as_view(), name="patient_list"),
    path("<uuid:pk>/", views.PatientDetailView.as_view(), name="patient_detail"),
    path(
        "<uuid:patient_id>/timeline/",
        PatientEventsTimelineView.as_view(),
        name="patient_events_timeline",
    ),
    path("create/", views.PatientCreateView.as_view(), name="patient_create"),
    path("<uuid:pk>/update/", views.PatientUpdateView.as_view(), name="patient_update"),
    path("<uuid:pk>/delete/", views.PatientDeleteView.as_view(), name="patient_delete"),
    path("<uuid:pk>/restore/", views.PatientRestoreView.as_view(), name="patient_restore"),
    # Patient Record Number URLs
    path(
        "<uuid:patient_id>/record-number/create/",
        views.PatientRecordNumberCreateView.as_view(),
        name="record_number_create",
    ),
    path(
        "record-number/<uuid:pk>/edit/",
        views.PatientRecordNumberUpdateView.as_view(),
        name="record_number_update",
    ),
    path(
        "record-number/<uuid:pk>/delete/",
        views.PatientRecordNumberDeleteView.as_view(),
        name="record_number_delete",
    ),
    path(
        "<uuid:patient_id>/record-number/quick-update/",
        views.QuickRecordNumberUpdateView.as_view(),
        name="quick_record_number_update",
    ),
    # Patient Admission URLs
    path(
        "<uuid:patient_id>/admit/",
        views.PatientAdmissionCreateView.as_view(),
        name="create_admission",
    ),
    path(
        "admission/<uuid:pk>/edit/",
        views.PatientAdmissionUpdateView.as_view(),
        name="admission_update",
    ),
    path(
        "admission/<uuid:pk>/discharge/",
        views.PatientDischargeView.as_view(),
        name="discharge_patient",
    ),
    path(
        "<uuid:patient_id>/quick-admit/",
        views.QuickAdmissionView.as_view(),
        name="quick_admit_patient",
    ),
    path(
        "admission/<uuid:admission_id>/quick-discharge/",
        views.QuickDischargeView.as_view(),
        name="quick_discharge_patient",
    ),
    # Status Change URLs
    path(
        "<uuid:pk>/status/admit/",
        views.AdmitPatientView.as_view(),
        name="admit_patient",
    ),
    path(
        "<uuid:pk>/status/discharge/",
        views.DischargePatientView.as_view(),
        name="discharge_patient",
    ),
    path(
        "<uuid:pk>/status/emergency/",
        views.EmergencyAdmissionView.as_view(),
        name="emergency_admission",
    ),
    path(
        "<uuid:pk>/status/transfer/",
        views.TransferPatientView.as_view(),
        name="transfer_patient",
    ),
    path(
        "<uuid:pk>/status/declare-death/",
        views.DeclareDeathView.as_view(),
        name="declare_death",
    ),
    path(
        "<uuid:pk>/status/set-outpatient/",
        views.SetOutpatientView.as_view(),
        name="set_outpatient",
    ),
    # Ward management URLs
    path("wards/", views.WardListView.as_view(), name="ward_list"),
    path("wards/add/", views.WardCreateView.as_view(), name="ward_create"),
    path("wards/<uuid:pk>/", views.WardDetailView.as_view(), name="ward_detail"),
    path("wards/<uuid:pk>/edit/", views.WardUpdateView.as_view(), name="ward_update"),
    # Tag URLs
    path("tags/", views.AllowedTagListView.as_view(), name="tag_list"),
    path("tags/create/", views.AllowedTagCreateView.as_view(), name="tag_create"),
    path(
        "tags/<int:pk>/update/", views.AllowedTagUpdateView.as_view(), name="tag_update"
    ),
    path(
        "tags/<int:pk>/delete/", views.AllowedTagDeleteView.as_view(), name="tag_delete"
    ),
    # Patient Tag Management URLs
    path(
        "<uuid:patient_id>/tags/add/", 
        views.PatientTagAddView.as_view(), 
        name="patient_tag_add"
    ),
    path(
        "<uuid:patient_id>/tags/<uuid:tag_id>/remove/", 
        views.PatientTagRemoveView.as_view(), 
        name="patient_tag_remove"
    ),
    path(
        "<uuid:patient_id>/tags/remove-all/", 
        views.PatientTagRemoveAllView.as_view(), 
        name="patient_tag_remove_all"
    ),
    path(
        "<uuid:patient_id>/tags/api/", 
        views.PatientTagsAPIView.as_view(), 
        name="patient_tags_api"
    ),
    # API URLs
    path(
        "api/<uuid:patient_id>/record-numbers/",
        views.PatientRecordNumbersAPIView.as_view(),
        name="api_patient_record_numbers",
    ),
    path(
        "api/<uuid:patient_id>/admissions/",
        views.PatientAdmissionsAPIView.as_view(),
        name="api_patient_admissions",
    ),
    path(
        "api/record-number/<str:record_number>/",
        views.RecordNumberLookupAPIView.as_view(),
        name="api_record_number_lookup",
    ),
    path(
        "api/admission/<uuid:admission_id>/",
        views.AdmissionDetailAPIView.as_view(),
        name="api_admission_detail",
    ),
    path(
        "api/patients/search/",
        views.PatientSearchAPIView.as_view(),
        name="api_patient_search",
    ),
]
