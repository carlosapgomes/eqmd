from django.urls import path
from . import views

app_name = 'apps.core'  # Or simply 'core', but 'apps.core' is more explicit given the structure

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
