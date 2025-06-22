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
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from .models import Photo, MediaFile
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


# Placeholder forms for future implementation
class PhotoSeriesUploadForm(BaseMediaForm):
    """Form for photo series uploads - to be implemented in future phase"""
    pass


class VideoUploadForm(BaseMediaForm):
    """Form for video clip uploads - to be implemented in future phase"""
    pass
