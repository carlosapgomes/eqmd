from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    # Patient URLs
    path('', views.PatientListView.as_view(), name='patient_list'),
    path('<uuid:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('create/', views.PatientCreateView.as_view(), name='patient_create'),
    path('<uuid:pk>/update/', views.PatientUpdateView.as_view(), name='patient_update'),
    path('<uuid:pk>/delete/', views.PatientDeleteView.as_view(), name='patient_delete'),

    # Hospital Record URLs
    path('<uuid:patient_id>/records/create/', views.HospitalRecordCreateView.as_view(), name='hospital_record_create'),
    path('records/<uuid:pk>/update/', views.HospitalRecordUpdateView.as_view(), name='hospital_record_update'),
    path('records/<uuid:pk>/delete/', views.HospitalRecordDeleteView.as_view(), name='hospital_record_delete'),

    # Tag URLs
    path('tags/', views.AllowedTagListView.as_view(), name='tag_list'),
    path('tags/create/', views.AllowedTagCreateView.as_view(), name='tag_create'),
    path('tags/<int:pk>/update/', views.AllowedTagUpdateView.as_view(), name='tag_update'),
    path('tags/<int:pk>/delete/', views.AllowedTagDeleteView.as_view(), name='tag_delete'),
]