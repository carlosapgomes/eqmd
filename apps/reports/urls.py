"""
URL configuration for reports app.
"""

from django.urls import path

from .views.pdf_views import ReportPDFView
from .views.report_tag_lookup import ReportTagLookupView
from .views.report_views import (
    ReportCreateView,
    ReportDeleteView,
    ReportDetailView,
    ReportDuplicateView,
    ReportUpdateView,
)
from .views.template_catalogue_filters import TemplateCatalogueFilterActionsView
from .views.template_selection_views import TemplateSelectionView
from .views.template_views import (
    TemplateCreateView,
    TemplateDeleteView,
    TemplateUpdateView,
)

app_name = 'reports'

urlpatterns = [
    # Template URLs
    path('templates/', TemplateCatalogueFilterActionsView.as_view(), name='template_list'),
    path('templates/tag-lookup/', ReportTagLookupView.as_view(), name='template_tag_lookup'),
    path('templates/select/', TemplateSelectionView.as_view(), name='template_select'),
    path('templates/create/', TemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/update/', TemplateUpdateView.as_view(), name='template_update'),
    path('templates/<uuid:pk>/delete/', TemplateDeleteView.as_view(), name='template_delete'),

    # Report URLs
    path('create/<uuid:patient_id>/', ReportCreateView.as_view(), name='report_create'),
    path('<uuid:pk>/', ReportDetailView.as_view(), name='report_detail'),
    path('<uuid:pk>/update/', ReportUpdateView.as_view(), name='report_update'),
    path('<uuid:pk>/duplicate/', ReportDuplicateView.as_view(), name='report_duplicate'),
    path('<uuid:pk>/delete/', ReportDeleteView.as_view(), name='report_delete'),
    path('<uuid:pk>/pdf/', ReportPDFView.as_view(), name='report_pdf'),
]
