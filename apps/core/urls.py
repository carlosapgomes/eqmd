from django.urls import path
from . import views
from . import test_views
from . import test_views_hospital_context

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Permission test URLs
    path('test/permissions/', test_views.permission_test_view, name='permission_test'),
    path('test/doctor-only/', test_views.doctor_only_view, name='doctor_only_test'),
    path('test/hospital-context/', test_views.hospital_context_view, name='hospital_context_test'),
    path('test/patient-access/<uuid:patient_id>/', test_views.patient_access_view, name='patient_access_test'),
    path('test/event-edit/<uuid:event_id>/', test_views.event_edit_view, name='event_edit_test'),
    
    # Hospital context test URLs
    path('test/hospital-context-middleware/', test_views_hospital_context.hospital_context_test_view, name='hospital_context_middleware_test'),
    path('test/hospital-context-required/', test_views_hospital_context.hospital_context_required_view, name='hospital_context_required_test'),
    path('test/hospital-context-api/', test_views_hospital_context.hospital_context_api_view, name='hospital_context_api_test'),
]
