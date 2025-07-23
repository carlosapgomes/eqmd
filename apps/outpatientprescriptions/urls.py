from django.urls import path
from . import views

app_name = 'outpatientprescriptions'

urlpatterns = [
    path('', views.OutpatientPrescriptionListView.as_view(), name='outpatientprescription_list'),
    path('create/', views.OutpatientPrescriptionCreateView.as_view(), name='outpatientprescription_create'),
    path('create/<uuid:patient_uuid>/', views.OutpatientPrescriptionCreateView.as_view(), name='outpatientprescription_create_for_patient'),
    path('<uuid:pk>/', views.OutpatientPrescriptionDetailView.as_view(), name='outpatientprescription_detail'),
    path('<uuid:pk>/edit/', views.OutpatientPrescriptionUpdateView.as_view(), name='outpatientprescription_update'),
    path('<uuid:pk>/delete/', views.OutpatientPrescriptionDeleteView.as_view(), name='outpatientprescription_delete'),
    path('<uuid:pk>/print/', views.OutpatientPrescriptionPrintView.as_view(), name='outpatientprescription_print'),
    path('<uuid:pk>/pdf/', views.OutpatientPrescriptionPDFView.as_view(), name='outpatientprescription_pdf'),
    
    # AJAX endpoints
    path('ajax/drug-template/<uuid:template_id>/', views.get_drug_template_data, name='get_drug_template_data'),
    path('ajax/drug-templates/search/', views.search_drug_templates, name='search_drug_templates'),
    path('ajax/prescription-template/<uuid:template_id>/', views.get_prescription_template_data, name='get_prescription_template_data'),
]