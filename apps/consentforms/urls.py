from django.urls import path
from . import views

app_name = "consentforms"

urlpatterns = [
    path("patient/<uuid:patient_pk>/create/", views.ConsentFormCreateView.as_view(), name="consentform_create"),
    path("<uuid:pk>/", views.ConsentFormDetailView.as_view(), name="consentform_detail"),
    path("<uuid:pk>/update/", views.ConsentFormUpdateView.as_view(), name="consentform_update"),
    path("<uuid:pk>/delete/", views.ConsentFormDeleteView.as_view(), name="consentform_delete"),
    path("<uuid:pk>/attachments/zip/", views.ConsentFormAttachmentsZipView.as_view(), name="consentform_attachments_zip"),
    path("<uuid:pk>/pdf/", views.ConsentFormPDFView.as_view(), name="consentform_pdf"),
    path("attachments/<uuid:pk>/delete/", views.ConsentAttachmentDeleteView.as_view(), name="consentattachment_delete"),
]
