# MediaFiles URLs
# URL patterns for media file management

from django.urls import path, include
from . import views

app_name = 'mediafiles'

urlpatterns = [
    # Secure file serving endpoints
    path('serve/<uuid:file_id>/', views.serve_media_file, name='serve_file'),
    path('thumbnail/<uuid:file_id>/', views.serve_thumbnail, name='serve_thumbnail'),

    # Class-based secure serving views
    path('secure/<uuid:file_id>/', views.SecureFileServeView.as_view(), name='secure_serve'),
    path('secure/thumbnail/<uuid:file_id>/', views.SecureThumbnailServeView.as_view(), name='secure_thumbnail'),

    # Placeholder patterns for future implementation
    # path('', views.MediaFileListView.as_view(), name='list'),
    # path('photo/', include([
    #     path('upload/', views.PhotoUploadView.as_view(), name='photo_upload'),
    #     path('<uuid:pk>/', views.PhotoDetailView.as_view(), name='photo_detail'),
    # ])),
    # path('series/', include([
    #     path('upload/', views.PhotoSeriesUploadView.as_view(), name='series_upload'),
    #     path('<uuid:pk>/', views.PhotoSeriesDetailView.as_view(), name='series_detail'),
    # ])),
    # path('video/', include([
    #     path('upload/', views.VideoUploadView.as_view(), name='video_upload'),
    #     path('<uuid:pk>/', views.VideoDetailView.as_view(), name='video_detail'),
    # ])),
]
