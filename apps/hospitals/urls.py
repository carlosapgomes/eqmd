from django.urls import path
from . import views

app_name = 'hospitals'

urlpatterns = [
    path('', views.HospitalListView.as_view(), name='list'),
    path('create/', views.HospitalCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.HospitalDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.HospitalUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.HospitalDeleteView.as_view(), name='delete'),
    
    # Ward URLs
    path('wards/', views.WardListView.as_view(), name='ward_list'),
    path('wards/<int:pk>/', views.WardDetailView.as_view(), name='ward_detail'),
    path('wards/create/', views.WardCreateView.as_view(), name='ward_create'),
    path('wards/<int:pk>/update/', views.WardUpdateView.as_view(), name='ward_update'),
    path('wards/<int:pk>/delete/', views.WardDeleteView.as_view(), name='ward_delete'),
    
    # Test URL
    path('test/ward-tags/', views.test_ward_tags, name='test_ward_tags'),
]