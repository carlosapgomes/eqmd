"""
URL configuration for reports app.
"""

from django.urls import path
from .views.template_views import TemplateListView, TemplateCreateView, TemplateUpdateView
from .views.report_views import ReportCreateView

app_name = 'reports'

urlpatterns = [
    path('templates/', TemplateListView.as_view(), name='template_list'),
    path('templates/create/', TemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/update/', TemplateUpdateView.as_view(), name='template_update'),
    path('create/<uuid:patient_id>/', ReportCreateView.as_view(), name='report_create'),
]
