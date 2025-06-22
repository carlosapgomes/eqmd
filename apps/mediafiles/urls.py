"""
MediaFiles URLs

URL patterns for media file management in EquipeMed.
Provides secure file serving and photo CRUD operations.
"""

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

    # Photo CRUD operations
    path('photos/', include([
        path('create/<uuid:patient_id>/', views.PhotoCreateView.as_view(), name='photo_create'),
        path('<uuid:pk>/', views.PhotoDetailView.as_view(), name='photo_detail'),
        path('<uuid:pk>/edit/', views.PhotoUpdateView.as_view(), name='photo_update'),
        path('<uuid:pk>/delete/', views.PhotoDeleteView.as_view(), name='photo_delete'),
        path('<uuid:pk>/download/', views.PhotoDownloadView.as_view(), name='photo_download'),
    ])),

    # Placeholder patterns for future implementation
    # path('series/', include([
    #     path('upload/', views.PhotoSeriesUploadView.as_view(), name='series_upload'),
    #     path('<uuid:pk>/', views.PhotoSeriesDetailView.as_view(), name='series_detail'),
    # ])),
    # path('video/', include([
    #     path('upload/', views.VideoUploadView.as_view(), name='video_upload'),
    #     path('<uuid:pk>/', views.VideoDetailView.as_view(), name='video_detail'),
    # ])),
]
