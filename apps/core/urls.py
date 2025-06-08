from django.urls import path
from . import views
from . import test_views
from . import test_views_hospital_context
from . import test_views_role_permissions

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
    path('test/patient-data-change/<uuid:patient_id>/', test_views.patient_data_change_view, name='patient_data_change_test'),
    path('test/event-delete/<uuid:event_id>/', test_views.event_delete_view, name='event_delete_test'),
    path('test/object-level-permissions/', test_views.object_level_permissions_test_view, name='object_level_permissions_test'),
    
    # Hospital context test URLs
    path('test/hospital-context-middleware/', test_views_hospital_context.hospital_context_test_view, name='hospital_context_middleware_test'),
    path('test/hospital-context-required/', test_views_hospital_context.hospital_context_required_view, name='hospital_context_required_test'),
    path('test/hospital-context-api/', test_views_hospital_context.hospital_context_api_view, name='hospital_context_api_test'),

    # Role-based permissions test URLs
    path('test/role-permissions/', test_views_role_permissions.role_permissions_test_view, name='role_permissions_test'),
    path('test/role-permissions-api/', test_views_role_permissions.role_permissions_api_view, name='role_permissions_api'),
    path('test/template-tags/', test_views_role_permissions.test_template_tags_view, name='test_template_tags'),
]
