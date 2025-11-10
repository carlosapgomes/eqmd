from django.urls import path
from . import views

app_name = 'apps.research'

urlpatterns = [
    path('', views.clinical_search, name='clinical_search'),
    path('search-ajax/', views.search_ajax, name='search_ajax'),
    path('export/', views.export_search_results, name='export_search_results'),
]