# MediaFiles Forms
# Forms for media file upload and management

from django import forms


class BaseMediaForm(forms.Form):
    """Base form for media file uploads"""
    pass


class PhotoUploadForm(BaseMediaForm):
    """Form for single photo uploads"""
    pass


class PhotoSeriesUploadForm(BaseMediaForm):
    """Form for photo series uploads"""
    pass


class VideoUploadForm(BaseMediaForm):
    """Form for video clip uploads"""
    pass
