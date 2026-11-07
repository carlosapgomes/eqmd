from django.urls import path

from . import views
from .views import national_forms
from .views.exam_batch import ExamRequestBatchView
from .views.exam_batch_download import ExamBatchDownloadView

app_name = 'pdf_forms'

urlpatterns = [
    # Template management
    path('templates/', views.PDFFormTemplateListView.as_view(), name='template_list'),
    path('template/<uuid:pk>/preview/', views.PDFFormTemplatePreviewView.as_view(), name='template_preview'),

    # Form workflow (hospital forms)
    path('select/<uuid:patient_id>/', views.PDFFormSelectView.as_view(), name='form_select'),
    path('fill/<uuid:template_id>/<uuid:patient_id>/', views.PDFFormFillView.as_view(), name='form_fill'),

    # Batch exam requests (chequinho lot capture, S1)
    path('exam-batch/download/<uuid:batch_id>/', ExamBatchDownloadView.as_view(), name='exam_batch_download'),
    path('exam-batch/<uuid:patient_id>/', ExamRequestBatchView.as_view(), name='exam_batch'),

    # National forms (APAC/AIH)
    path('apac/<uuid:patient_id>/', national_forms.APACFormView.as_view(), name='apac_form'),
    path('aih/<uuid:patient_id>/', national_forms.AIHFormView.as_view(), name='aih_form'),

    # Submissions
    path('submission/<uuid:pk>/', views.PDFFormSubmissionDetailView.as_view(), name='submission_detail'),
    path('submission/<uuid:pk>/edit/', views.PDFFormSubmissionUpdateView.as_view(), name='submission_update'),
    path('apac/submission/<uuid:pk>/edit/', national_forms.APACFormUpdateView.as_view(), name='apac_submission_update'),
    path('submission/<uuid:pk>/duplicate/', views.PDFFormSubmissionDuplicateView.as_view(), name='submission_duplicate'),
    path('submission/<uuid:pk>/delete/', views.PDFFormSubmissionDeleteView.as_view(), name='submission_delete'),
    path('download/<uuid:submission_id>/', views.PDFFormDownloadView.as_view(), name='pdf_download'),
]