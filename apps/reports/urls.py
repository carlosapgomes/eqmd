"""
URL configuration for reports app.
"""

from django.urls import path
from .views.template_views import TemplateListView, TemplateCreateView, TemplateUpdateView
from .views.report_views import (
    ReportCreateView,
    ReportDetailView,
    ReportUpdateView,
    ReportDeleteView,
)

app_name = 'reports'

urlpatterns = [
    # Template URLs
    path('templates/', TemplateListView.as_view(), name='template_list'),
    path('templates/create/', TemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/update/', TemplateUpdateView.as_view(), name='template_update'),

    # Report URLs
    path('create/<uuid:patient_id>/', ReportCreateView.as_view(), name='report_create'),
    path('<uuid:pk>/', ReportDetailView.as_view(), name='report_detail'),
    path('<uuid:pk>/update/', ReportUpdateView.as_view(), name='report_update'),
    path('<uuid:pk>/delete/', ReportDeleteView.as_view(), name='report_delete'),
]
