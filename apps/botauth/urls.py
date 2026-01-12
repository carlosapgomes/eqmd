from django.urls import path
from . import views
from .api_views import DelegatedTokenView

app_name = 'botauth'

urlpatterns = [
    # Human-facing views
    path('matrix/bind/', 
         views.MatrixBindingCreateView.as_view(), 
         name='binding_create'),
    path('matrix/status/', 
         views.MatrixBindingStatusView.as_view(), 
         name='binding_status'),
    path('matrix/verify/<str:token>/', 
         views.MatrixBindingVerifyView.as_view(), 
         name='binding_verify'),
    path('matrix/revoke/<uuid:pk>/', 
         views.MatrixBindingDeleteView.as_view(), 
         name='binding_delete'),
    
    # Bot API endpoints
    path('api/delegated-token/', DelegatedTokenView.as_view(), name='delegated_token'),
]