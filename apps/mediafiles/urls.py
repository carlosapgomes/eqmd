"""
MediaFiles URLs

URL patterns for media file management in EquipeMed.
Provides secure file serving and photo CRUD operations.
"""

from django.urls import path, include
from . import views

app_name = 'mediafiles'

urlpatterns = [
    # FilePond URLs
    path('fp/', include('django_drf_filepond.urls')),

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

    # PhotoSeries CRUD operations
    path('photo-series/', include([
        path('create/<uuid:patient_id>/', views.PhotoSeriesCreateView.as_view(), name='photoseries_create'),
        path('<uuid:pk>/', views.PhotoSeriesDetailView.as_view(), name='photoseries_detail'),
        path('<uuid:pk>/edit/', views.PhotoSeriesUpdateView.as_view(), name='photoseries_update'),
        path('<uuid:pk>/delete/', views.PhotoSeriesDeleteView.as_view(), name='photoseries_delete'),
        path('<uuid:pk>/download/', views.photoseries_download, name='photoseries_download'),
        # AJAX endpoints
        path('<uuid:pk>/add-photo/', views.photoseries_add_photo, name='photoseries_add_photo'),
        path('<uuid:pk>/remove-photo/<uuid:photo_id>/', views.photoseries_remove_photo, name='photoseries_remove_photo'),
        path('<uuid:pk>/reorder/', views.photoseries_reorder, name='photoseries_reorder'),
    ])),

    # VideoClip CRUD operations
    path('videos/', include([
        path('create/<uuid:patient_id>/', views.VideoClipCreateView.as_view(), name='videoclip_create'),
        path('<uuid:pk>/', views.VideoClipDetailView.as_view(), name='videoclip_detail'),
        path('<uuid:pk>/edit/', views.VideoClipUpdateView.as_view(), name='videoclip_update'),
        path('<uuid:pk>/delete/', views.VideoClipDeleteView.as_view(), name='videoclip_delete'),
        path('<uuid:pk>/stream/', views.VideoClipStreamView.as_view(), name='videoclip_stream'),
        path('<uuid:pk>/download/', views.VideoClipDownloadView.as_view(), name='videoclip_download'),
    ])),
]
