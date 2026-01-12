from django.urls import path
from . import views
from .views import national_forms

app_name = 'pdf_forms'

urlpatterns = [
    # Template management
    path('templates/', views.PDFFormTemplateListView.as_view(), name='template_list'),

    # Form workflow (hospital forms)
    path('select/<uuid:patient_id>/', views.PDFFormSelectView.as_view(), name='form_select'),
    path('fill/<uuid:template_id>/<uuid:patient_id>/', views.PDFFormFillView.as_view(), name='form_fill'),

    # National forms (APAC/AIH)
    path('apac/<uuid:patient_id>/', national_forms.APACFormView.as_view(), name='apac_form'),
    path('aih/<uuid:patient_id>/', national_forms.AIHFormView.as_view(), name='aih_form'),

    # Submissions
    path('submission/<uuid:pk>/', views.PDFFormSubmissionDetailView.as_view(), name='submission_detail'),
    path('submission/<uuid:pk>/delete/', views.PDFFormSubmissionDeleteView.as_view(), name='submission_delete'),
    path('download/<uuid:submission_id>/', views.PDFFormDownloadView.as_view(), name='pdf_download'),
]