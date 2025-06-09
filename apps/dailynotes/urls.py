from django.urls import path
from . import views

app_name = 'dailynotes'

urlpatterns = [
    # DailyNote CRUD URLs
    path('', views.DailyNoteListView.as_view(), name='dailynote_list'),
    path('<uuid:pk>/', views.DailyNoteDetailView.as_view(), name='dailynote_detail'),
    path('create/', views.DailyNoteCreateView.as_view(), name='dailynote_create'),
    path('<uuid:pk>/update/', views.DailyNoteUpdateView.as_view(), name='dailynote_update'),
    path('<uuid:pk>/delete/', views.DailyNoteDeleteView.as_view(), name='dailynote_delete'),
]
