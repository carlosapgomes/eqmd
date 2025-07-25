from django.urls import path
from . import views

app_name = 'pdf_forms'

urlpatterns = [
    # Template management
    path('templates/', views.PDFFormTemplateListView.as_view(), name='template_list'),

    # Form workflow
    path('select/<uuid:patient_id>/', views.PDFFormSelectView.as_view(), name='form_select'),
    path('fill/<uuid:template_id>/<uuid:patient_id>/', views.PDFFormFillView.as_view(), name='form_fill'),

    # Submissions
    path('submission/<uuid:pk>/', views.PDFFormSubmissionDetailView.as_view(), name='submission_detail'),
    path('download/<uuid:submission_id>/', views.PDFFormDownloadView.as_view(), name='pdf_download'),
]