from django.urls import path
from . import views
from . import test_views
# from . import test_views_hospital_context  # Temporarily disabled for single-hospital refactor
from . import test_views_role_permissions
from . import permission_demo

app_name = "apps.core"

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("health/", views.health_check, name="health_check"),
    path("manifest.json", views.manifest_json, name="manifest_json"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path(
        "password-change-required/", 
        views.PasswordChangeRequiredView.as_view(), 
        name="password_change_required"
    ),
    # Permission test URLs
    path("test/permissions/", test_views.permission_test_view, name="permission_test"),
    path("test/doctor-only/", test_views.doctor_only_view, name="doctor_only_test"),
    # path(
    #     "test/hospital-context/",
    #     test_views.hospital_context_view,
    #     name="hospital_context_test",
    # ),  # Removed for single-hospital refactor
    path(
        "test/patient-access/<uuid:patient_id>/",
        test_views.patient_access_view,
        name="patient_access_test",
    ),
    path(
        "test/event-edit/<uuid:event_id>/",
        test_views.event_edit_view,
        name="event_edit_test",
    ),
    path(
        "test/patient-data-change/<uuid:patient_id>/",
        test_views.patient_data_change_view,
        name="patient_data_change_test",
    ),
    path(
        "test/event-delete/<uuid:event_id>/",
        test_views.event_delete_view,
        name="event_delete_test",
    ),
    path(
        "test/object-level-permissions/",
        test_views.object_level_permissions_test_view,
        name="object_level_permissions_test",
    ),
    # Hospital context test URLs - Temporarily disabled for single-hospital refactor
    # path(
    #     "test/hospital-context-middleware/",
    #     test_views_hospital_context.hospital_context_test_view,
    #     name="hospital_context_middleware_test",
    # ),
    # path(
    #     "test/hospital-context-required/",
    #     test_views_hospital_context.hospital_context_required_view,
    #     name="hospital_context_required_test",
    # ),
    # path(
    #     "test/hospital-context-api/",
    #     test_views_hospital_context.hospital_context_api_view,
    #     name="hospital_context_api_test",
    # ),
    # Role-based permissions test URLs
    path(
        "test/role-permissions/",
        test_views_role_permissions.role_permissions_test_view,
        name="role_permissions_test",
    ),
    path(
        "test/role-permissions-api/",
        test_views_role_permissions.role_permissions_api_view,
        name="role_permissions_api",
    ),
    path(
        "test/template-tags/",
        test_views_role_permissions.test_template_tags_view,
        name="test_template_tags",
    ),
    # Performance and UI integration test URLs
    path(
        "test/permission-performance/",
        views.permission_performance_test,
        name="permission_performance_test",
    ),
    path(
        "test/permission-performance-api/",
        views.permission_performance_api,
        name="permission_performance_api",
    ),
    # Permission System Demo URLs
    path(
        "demo/permissions/",
        permission_demo.permission_demo_dashboard,
        name="permission_demo_dashboard",
    ),
    path(
        "demo/permissions/api/",
        permission_demo.permission_demo_api,
        name="permission_demo_api",
    ),
    path(
        "demo/permissions/patient/<str:patient_id>/",
        permission_demo.demo_patient_detail,
        name="permission_demo_patient",
    ),
    path(
        "demo/permissions/doctor-only/",
        permission_demo.demo_doctor_only,
        name="permission_demo_doctor",
    ),
    # path(
    #     "demo/permissions/hospital-context/",
    #     permission_demo.demo_hospital_context,
    #     name="permission_demo_hospital",
    # ),  # Removed for single-hospital refactor
    path(
        "demo/permissions/cache/",
        permission_demo.demo_cache_management,
        name="permission_demo_cache",
    ),
    path(
        "demo/permissions/test/",
        permission_demo.demo_permission_test,
        name="permission_demo_test",
    ),
    path(
        "demo/permissions/comparison/",
        permission_demo.demo_role_comparison,
        name="permission_demo_comparison",
    ),
]
