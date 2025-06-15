from django.urls import path
from . import views

app_name = 'sample_content'

urlpatterns = [
    path('', views.SampleContentListView.as_view(), name='list'),
    path('api/event-type/<str:event_type>/', views.sample_content_by_event_type, name='api_by_event_type'),
]