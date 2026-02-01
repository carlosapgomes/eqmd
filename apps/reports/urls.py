"""
URL configuration for reports app.
"""

from django.urls import path
from .views.template_views import TemplateListView, TemplateCreateView, TemplateUpdateView

app_name = 'reports'

urlpatterns = [
    path('templates/', TemplateListView.as_view(), name='template_list'),
    path('templates/create/', TemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/update/', TemplateUpdateView.as_view(), name='template_update'),
]
