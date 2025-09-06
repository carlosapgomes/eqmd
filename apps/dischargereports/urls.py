from django.urls import path
from . import views

app_name = 'apps.dischargereports'

urlpatterns = [
    path('', views.DischargeReportListView.as_view(), name='dischargereport_list'),
    path('create/', views.DischargeReportCreateView.as_view(), name='dischargereport_create'),
    path('<uuid:pk>/', views.DischargeReportDetailView.as_view(), name='dischargereport_detail'),
    path('<uuid:pk>/update/', views.DischargeReportUpdateView.as_view(), name='dischargereport_update'),
    path('<uuid:pk>/delete/', views.DischargeReportDeleteView.as_view(), name='dischargereport_delete'),
]