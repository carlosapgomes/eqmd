"""
MediaFiles Forms

This module implements forms for media file upload and management in EquipeMed.
It provides secure file upload forms with validation and Bootstrap styling.

Forms:
- PhotoCreateForm: For creating new photo events
- PhotoUpdateForm: For updating existing photo events
- BaseMediaForm: Base form for media file uploads
"""

import os
from pathlib import Path
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from .models import Photo, MediaFile, PhotoSeries, VideoClip
from apps.events.models import Event


class BaseMediaForm(forms.Form):
    """Base form for media file uploads with common validation"""

    def clean_event_datetime(self):
        """Ensure event datetime is not in the future"""
        event_datetime = self.cleaned_data.get('event_datetime')
        if event_datetime and event_datetime > timezone.now():
            raise ValidationError("A data e hora do evento não pode ser no futuro.")
        return event_datetime


class PhotoCreateForm(BaseMediaForm, forms.ModelForm):
    """
    Form for creating new photo events.

    Handles file upload, validation, and secure MediaFile creation.
    """

    image = forms.FileField(
        label="Imagem",
        help_text="Selecione uma imagem (JPEG, PNG, WebP). Máximo 5MB.",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/webp',
            'data-preview': 'true'
        })
    )

    class Meta:
        model = Photo
        fields = ['description', 'event_datetime', 'caption']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição da foto (ex: Raio-X do tórax)',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Legenda opcional para a foto'
            })
        }

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set input formats for datetime field
        self.fields['event_datetime'].input_formats = [
            '%Y-%m-%dT%H:%M',  # HTML5 datetime-local format
            '%Y-%m-%dT%H:%M:%S',
            '%d/%m/%Y %H:%M:%S',  # Format in error message
            '%d/%m/%Y %H:%M',
        ]

        # Set default event datetime to now
        if not self.instance.pk:
            utc_now = timezone.now().astimezone(timezone.get_default_timezone())
            self.fields['event_datetime'].initial = utc_now.strftime('%Y-%m-%dT%H:%M')
        else:
            dt = self.instance.event_datetime.astimezone(timezone.get_default_timezone())
            self.fields['event_datetime'].initial = dt.strftime('%Y-%m-%dT%H:%M')

    def clean_image(self):
        """Validate uploaded image file"""
        image = self.cleaned_data.get('image')
        if not image:
            return image

        # File size validation
        max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)  # 5MB default
        if image.size > max_size:
            raise ValidationError(f"Arquivo muito grande. Máximo permitido: {max_size // (1024*1024)}MB")

        # File type validation
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', [
            'image/jpeg', 'image/png', 'image/webp'
        ])
        if image.content_type not in allowed_types:
            raise ValidationError("Tipo de arquivo não permitido. Use JPEG, PNG ou WebP.")

        # File extension validation
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', [
            '.jpg', '.jpeg', '.png', '.webp'
        ])
        file_extension = os.path.splitext(image.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError("Extensão de arquivo não permitida.")

        # Basic security validation
        self._validate_file_security(image)

        return image

    def _validate_file_security(self, file):
        """Perform basic security validation on uploaded file"""
        # Check for path traversal attempts
        if '..' in file.name or '/' in file.name or '\\' in file.name:
            raise ValidationError("Nome de arquivo inválido.")

        # Check file header for basic validation
        file.seek(0)
        header = file.read(1024)
        file.seek(0)

        # Basic image header validation
        if not (header.startswith(b'\xff\xd8\xff') or  # JPEG
                header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                header.startswith(b'RIFF') and b'WEBP' in header[:20]):  # WebP
            raise ValidationError("Arquivo não é uma imagem válida.")

    def save(self, commit=True):
        """Save photo with associated MediaFile"""
        photo = super().save(commit=False)

        # Set required fields
        photo.patient = self.patient
        photo.created_by = self.user
        photo.updated_by = self.user
        photo.event_type = Event.PHOTO_EVENT

        if commit:
            # Create MediaFile from uploaded image first
            image = self.cleaned_data['image']
            media_file = MediaFile.objects.create_from_upload(image)

            # Assign media_file before saving to avoid validation issues
            photo.media_file = media_file

            # Now save the photo with the media_file assigned
            photo.save()

        return photo


class PhotoUpdateForm(BaseMediaForm, forms.ModelForm):
    """
    Form for updating existing photo events.

    Does not allow changing the image file, only metadata.
    """

    class Meta:
        model = Photo
        fields = ['description', 'event_datetime', 'caption']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição da foto',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Legenda opcional para a foto'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set input formats for datetime field
        self.fields['event_datetime'].input_formats = [
            '%Y-%m-%dT%H:%M',  # HTML5 datetime-local format
            '%Y-%m-%dT%H:%M:%S',
            '%d/%m/%Y %H:%M:%S',  # Format in error message
            '%d/%m/%Y %H:%M',
        ]

        # Set proper initial value for existing instances
        if self.instance.pk and self.instance.event_datetime:
            dt = self.instance.event_datetime.astimezone(timezone.get_default_timezone())
            self.fields['event_datetime'].initial = dt.strftime('%Y-%m-%dT%H:%M')

    def save(self, commit=True):
        """Save photo updates"""
        photo = super().save(commit=False)

        # Update modified fields
        if self.user:
            photo.updated_by = self.user

        if commit:
            photo.save()

        return photo


class PhotoSeriesCreateForm(BaseMediaForm, forms.ModelForm):
    """
    Form for creating new photo series events.

    Handles multiple file upload, validation, and secure MediaFile creation.
    """

    # Note: Multiple file upload will be handled via JavaScript and AJAX
    # This field is for the primary image when creating a series
    images = forms.FileField(
        label="Imagem Principal",
        help_text="Selecione a primeira imagem da série (JPEG, PNG, WebP). Máximo 5MB.",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/webp',
            'data-preview': 'true'
        }),
        required=True
    )

    class Meta:
        model = PhotoSeries
        fields = ['description', 'event_datetime', 'caption']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição da série de fotos (ex: Evolução da ferida)',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Legenda opcional para a série de fotos'
            })
        }

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set input formats for datetime field
        self.fields['event_datetime'].input_formats = [
            '%Y-%m-%dT%H:%M',  # HTML5 datetime-local format
            '%Y-%m-%dT%H:%M:%S',
            '%d/%m/%Y %H:%M:%S',  # Format in error message
            '%d/%m/%Y %H:%M',
        ]

        # Set default event datetime to now
        if not self.instance.pk:
            utc_now = timezone.now().astimezone(timezone.get_default_timezone())
            self.fields['event_datetime'].initial = utc_now.strftime('%Y-%m-%dT%H:%M')
        else:
            dt = self.instance.event_datetime.astimezone(timezone.get_default_timezone())
            self.fields['event_datetime'].initial = dt.strftime('%Y-%m-%dT%H:%M')

    def clean_images(self):
        """Validate multiple uploaded image files"""
        # Handle both QueryDict (normal form submission) and dict (test cases)
        if hasattr(self.files, 'getlist'):
            files = self.files.getlist('images')
        else:
            # Fallback for test cases where files is a regular dict
            files = self.files.get('images', [])
            if not isinstance(files, list):
                files = [files] if files else []
        if not files:
            raise ValidationError("Pelo menos uma imagem deve ser selecionada.")

        # Validate each file individually
        validated_files = []
        total_size = 0

        for file in files:
            # File size validation
            max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)  # 5MB default
            if file.size > max_size:
                raise ValidationError(f"Arquivo {file.name} muito grande. Máximo permitido: {max_size // (1024*1024)}MB")

            # File type validation
            allowed_types = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', [
                'image/jpeg', 'image/png', 'image/webp'
            ])
            if file.content_type not in allowed_types:
                raise ValidationError(f"Tipo de arquivo não permitido para {file.name}. Use JPEG, PNG ou WebP.")

            # File extension validation
            allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', [
                '.jpg', '.jpeg', '.png', '.webp'
            ])
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError(f"Extensão de arquivo não permitida para {file.name}.")

            # Basic security validation
            self._validate_file_security(file)

            validated_files.append(file)
            total_size += file.size

        # Check total series size limit
        max_series_size = getattr(settings, 'MEDIA_SERIES_MAX_TOTAL_SIZE', 50 * 1024 * 1024)  # 50MB default
        if total_size > max_series_size:
            raise ValidationError(f"Tamanho total da série ({total_size // (1024*1024)}MB) excede o limite máximo ({max_series_size // (1024*1024)}MB).")

        return validated_files

    def clean(self):
        """Ensure at least one image and validate series constraints"""
        cleaned_data = super().clean()
        
        # Check if we have images
        images = cleaned_data.get('images', [])
        if not images:
            raise ValidationError("Uma série de fotos deve conter pelo menos uma imagem.")

        # Check maximum number of images per series
        max_images = getattr(settings, 'MEDIA_SERIES_MAX_IMAGES', 20)  # 20 images default
        if len(images) > max_images:
            raise ValidationError(f"Número máximo de imagens por série: {max_images}")

        return cleaned_data

    def _validate_file_security(self, file):
        """Perform basic security validation on uploaded file"""
        # Check for path traversal attempts
        if '..' in file.name or '/' in file.name or '\\' in file.name:
            raise ValidationError(f"Nome de arquivo inválido: {file.name}")

        # Check file header for basic validation
        file.seek(0)
        header = file.read(1024)
        file.seek(0)

        # Basic image header validation
        if not (header.startswith(b'\xff\xd8\xff') or  # JPEG
                header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                header.startswith(b'RIFF') and b'WEBP' in header[:20]):  # WebP
            raise ValidationError(f"Arquivo {file.name} não é uma imagem válida.")

    def validate_batch_security(self, files):
        """Comprehensive security validation for all files"""
        for file in files:
            self._validate_file_security(file)

    def save(self, commit=True):
        """Save photo series with associated MediaFiles"""
        photoseries = super().save(commit=False)

        # Set required fields
        photoseries.patient = self.patient
        photoseries.created_by = self.user
        photoseries.updated_by = self.user
        photoseries.event_type = Event.PHOTO_SERIES_EVENT

        if commit:
            # Save the PhotoSeries first to get an ID
            photoseries.save()

            # Create MediaFiles and add to series
            images = self.cleaned_data['images']
            photoseries.add_photos_batch(images)

        return photoseries


class PhotoSeriesUpdateForm(BaseMediaForm, forms.ModelForm):
    """
    Form for updating existing photo series events.

    Limited editing per extra requirements: only description, datetime, and caption.
    """

    class Meta:
        model = PhotoSeries
        fields = ['description', 'event_datetime', 'caption']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição da série de fotos',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Legenda opcional para a série de fotos'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set input formats for datetime field
        self.fields['event_datetime'].input_formats = [
            '%Y-%m-%dT%H:%M',  # HTML5 datetime-local format
            '%Y-%m-%dT%H:%M:%S',
            '%d/%m/%Y %H:%M:%S',  # Format in error message
            '%d/%m/%Y %H:%M',
        ]

        # Set proper initial value for existing instances
        if self.instance.pk and self.instance.event_datetime:
            dt = self.instance.event_datetime.astimezone(timezone.get_default_timezone())
            self.fields['event_datetime'].initial = dt.strftime('%Y-%m-%dT%H:%M')

    def save(self, commit=True):
        """Save photo series updates"""
        photoseries = super().save(commit=False)

        # Update modified fields
        if self.user:
            photoseries.updated_by = self.user

        if commit:
            photoseries.save()

        return photoseries


class PhotoSeriesPhotoForm(forms.Form):
    """
    Form for adding individual photos to existing series.
    AJAX-compatible for dynamic addition.
    """

    image = forms.FileField(
        label="Imagem",
        help_text="Selecione uma imagem (JPEG, PNG, WebP). Máximo 5MB.",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/webp',
            'data-preview': 'true'
        })
    )

    description = forms.CharField(
        label="Descrição",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Descrição opcional para esta foto'
        })
    )

    order = forms.IntegerField(
        label="Ordem",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ordem na série (opcional)'
        })
    )

    def clean_image(self):
        """Validate uploaded image file"""
        image = self.cleaned_data.get('image')
        if not image:
            return image

        # File size validation
        max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)  # 5MB default
        if image.size > max_size:
            raise ValidationError(f"Arquivo muito grande. Máximo permitido: {max_size // (1024*1024)}MB")

        # File type validation
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', [
            'image/jpeg', 'image/png', 'image/webp'
        ])
        if image.content_type not in allowed_types:
            raise ValidationError("Tipo de arquivo não permitido. Use JPEG, PNG ou WebP.")

        # File extension validation
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', [
            '.jpg', '.jpeg', '.png', '.webp'
        ])
        file_extension = os.path.splitext(image.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError("Extensão de arquivo não permitida.")

        # Basic security validation
        self._validate_file_security(image)

        return image

    def _validate_file_security(self, file):
        """Perform basic security validation on uploaded file"""
        # Check for path traversal attempts
        if '..' in file.name or '/' in file.name or '\\' in file.name:
            raise ValidationError("Nome de arquivo inválido.")

        # Check file header for basic validation
        file.seek(0)
        header = file.read(1024)
        file.seek(0)

        # Basic image header validation
        if not (header.startswith(b'\xff\xd8\xff') or  # JPEG
                header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                header.startswith(b'RIFF') and b'WEBP' in header[:20]):  # WebP
            raise ValidationError("Arquivo não é uma imagem válida.")


class VideoClipCreateForm(BaseMediaForm, forms.ModelForm):
    """
    Form for creating new video clip events.

    Handles video file upload, validation, and secure MediaFile creation.
    """

    video = forms.FileField(
        label="Vídeo",
        help_text="Selecione um vídeo (MP4, WebM, MOV). Máximo 50MB e 2 minutos de duração.",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/webm,video/quicktime',
            'data-preview': 'true'
        })
    )

    class Meta:
        model = VideoClip
        fields = ['description', 'event_datetime', 'caption']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do vídeo (ex: Exercício de fisioterapia)',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Legenda opcional para o vídeo'
            })
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with user and patient context."""
        self.user = kwargs.pop('user', None)
        self.patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)

        # Set initial datetime to now
        if not self.instance.pk:
            self.fields['event_datetime'].initial = timezone.now()

    def clean_video(self):
        """Validate video file with comprehensive security checks."""
        video = self.cleaned_data.get('video')
        if not video:
            return video

        # Import video validation utilities
        from .utils import validate_video_file

        # Validate file size
        max_size = getattr(settings, 'MEDIA_VIDEO_MAX_SIZE', 50 * 1024 * 1024)  # 50MB
        if video.size > max_size:
            raise ValidationError(f"Arquivo muito grande. Tamanho máximo: {max_size // (1024 * 1024)}MB")

        # Validate file extension
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_VIDEO_EXTENSIONS', ['.mp4', '.webm', '.mov'])
        ext = Path(video.name).suffix.lower()
        if ext not in allowed_extensions:
            raise ValidationError(f"Formato de arquivo não permitido. Formatos aceitos: {', '.join(allowed_extensions)}")

        # Validate MIME type
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_VIDEO_TYPES', ['video/mp4', 'video/webm', 'video/quicktime'])
        if video.content_type not in allowed_types:
            raise ValidationError(f"Tipo de arquivo não permitido: {video.content_type}")

        # Validate video content and duration using ffmpeg
        validation_result = validate_video_file(video)
        if not validation_result['is_valid']:
            error_messages = '; '.join(validation_result['errors'])
            raise ValidationError(f"Arquivo de vídeo inválido: {error_messages}")

        # Check duration specifically
        if 'metadata' in validation_result and 'duration' in validation_result['metadata']:
            duration = validation_result['metadata']['duration']
            max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)  # 2 minutes
            if duration > max_duration:
                minutes = max_duration // 60
                seconds = max_duration % 60
                raise ValidationError(f"Duração do vídeo ({duration:.1f}s) excede o limite de {minutes}:{seconds:02d}")

        # Perform security validation
        try:
            from .utils import validate_video_upload_security
            security_result = validate_video_upload_security(video, video.name)
            if not security_result['is_secure']:
                security_issues = '; '.join(security_result['security_issues'])
                raise ValidationError(f"Problemas de segurança detectados: {security_issues}")
        except Exception as e:
            raise ValidationError(f"Erro na validação de segurança: {str(e)}")

        return video

    def save(self, commit=True):
        """Save video clip with secure MediaFile creation."""
        video_clip = super().save(commit=False)

        # Set required fields
        video_clip.patient = self.patient
        video_clip.created_by = self.user
        video_clip.updated_by = self.user

        if commit:
            # Create MediaFile from uploaded video
            video_file = self.cleaned_data['video']
            media_file = MediaFile.objects.create_from_upload(video_file)

            # Associate MediaFile with VideoClip
            video_clip.media_file = media_file
            video_clip.save()

        return video_clip


class VideoClipUpdateForm(BaseMediaForm, forms.ModelForm):
    """
    Form for updating existing video clip events.

    Limited editing per requirements: only description, datetime, and caption.
    Does not allow changing the video file.
    """

    class Meta:
        model = VideoClip
        fields = ['description', 'event_datetime', 'caption']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do vídeo',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Legenda opcional para o vídeo'
            })
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with current video clip data."""
        super().__init__(*args, **kwargs)

        # Format datetime for HTML5 datetime-local input
        if self.instance and self.instance.event_datetime:
            self.fields['event_datetime'].initial = self.instance.event_datetime.strftime('%Y-%m-%dT%H:%M')

    def save(self, commit=True):
        """Save updated video clip metadata."""
        video_clip = super().save(commit=False)

        # Update the updated_by field
        if hasattr(self, 'user') and self.user:
            video_clip.updated_by = self.user

        if commit:
            video_clip.save()

        return video_clip


# Legacy form for backward compatibility
class VideoUploadForm(VideoClipCreateForm):
    """Legacy form name for backward compatibility."""
    pass
