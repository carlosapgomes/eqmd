from django.urls import path
from . import views

app_name = 'drugtemplates'

urlpatterns = [
    # Drug Template URLs
    path('', views.DrugTemplateListView.as_view(), name='list'),
    path('create/', views.DrugTemplateCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.DrugTemplateDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.DrugTemplateUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.DrugTemplateDeleteView.as_view(), name='delete'),
    
    # Prescription Template URLs
    path('prescription-templates/', views.PrescriptionTemplateListView.as_view(), name='prescription_list'),
    path('prescription-templates/create/', views.PrescriptionTemplateCreateView.as_view(), name='prescription_create'),
    path('prescription-templates/<uuid:pk>/', views.PrescriptionTemplateDetailView.as_view(), name='prescription_detail'),
    path('prescription-templates/<uuid:pk>/edit/', views.PrescriptionTemplateUpdateView.as_view(), name='prescription_update'),
    path('prescription-templates/<uuid:pk>/delete/', views.PrescriptionTemplateDeleteView.as_view(), name='prescription_delete'),
]