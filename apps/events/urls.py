from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('patient/<uuid:patient_id>/', views.patient_events_list, name='patient_events_list'),
    path('user/', views.user_events_list, name='user_events_list'),
]