from django.urls import path
from . import views

app_name = 'compliance'

urlpatterns = [
    # Staff-only LGPD management URLs (no public access)
    path('admin/compliance/nova-solicitacao/', views.PatientDataRequestCreateView.as_view(), name='data_request_create'),
    path('admin/compliance/solicitacoes/', views.PatientDataRequestListView.as_view(), name='data_request_list'),
    path('admin/compliance/solicitacao/<str:request_id>/', views.PatientDataRequestDetailView.as_view(), name='data_request_detail'),
    path('admin/compliance/solicitacao/<str:request_id>/editar/', views.PatientDataRequestUpdateView.as_view(), name='data_request_update'),
    path('admin/compliance/export/<str:request_id>/', views.patient_data_export, name='patient_data_export'),
    
    # Privacy policy URLs
    path('privacidade/', views.privacy_policy, name='privacy_policy'),
    path('privacidade/<str:policy_type>/', views.privacy_policy, name='privacy_policy_type'),
    path('privacidade/<str:policy_type>/detalhes/', views.PrivacyPolicyDetailView.as_view(), name='privacy_policy_detail'),
    
    # Data processing notices
    path('aviso-processamento/<str:context>/', views.data_processing_notice, name='data_processing_notice'),
]