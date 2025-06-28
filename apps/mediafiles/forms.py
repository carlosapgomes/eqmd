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
import uuid
from pathlib import Path
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from .models import Photo, MediaFile, PhotoSeries, VideoClip, PhotoSeriesFile
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond.api import store_upload
from .video_processor import VideoProcessor
from .image_processor import ImageProcessor
from apps.events.models import Event


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads following Django 5.2 pattern"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field that handles multiple file uploads following Django 5.2 pattern"""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        """Clean multiple files"""
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


from apps.events.models import Event


class BaseMediaForm(forms.Form):
    """Base form for media file uploads with common validation"""

    def clean_event_datetime(self):
        """Ensure event datetime is not in the future"""
        event_datetime = self.cleaned_data.get('event_datetime')
        if event_datetime and event_datetime > timezone.now():
            raise ValidationError("A data e hora do evento não pode ser no futuro.")
        return event_datetime


class BaseEventForm(forms.ModelForm):
    """Base form for Event-based models with common validation"""

    def clean_event_datetime(self):
        """Ensure event datetime is not in the future"""
        event_datetime = self.cleaned_data.get('event_datetime')
        if event_datetime and event_datetime > timezone.now():
            raise ValidationError("A data e hora do evento não pode ser no futuro.")
        return event_datetime

    class Meta:
        fields = ['description', 'event_datetime']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do evento',
                'maxlength': 255
            }),
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
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

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.patient = self.patient
        instance.created_by = self.user
        instance.updated_by = self.user
        if commit:
            instance.save()
        return instance


# New FilePond-based forms
class PhotoCreateFormNew(BaseEventForm):
    """Simplified Photo form using FilePond."""
    
    upload_id = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="FilePond upload identifier"
    )
    
    caption = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Legenda"
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
    
    def clean_upload_id(self):
        upload_id = self.cleaned_data['upload_id']
        
        try:
            temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)
        except TemporaryUpload.DoesNotExist:
            raise forms.ValidationError("Upload not found or expired")
        
        # Validate it's an image file
        if not temp_upload.upload_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            raise forms.ValidationError("File must be an image")
        
        return upload_id
    
    def save(self, commit=True):
        photo = super().save(commit=False)
        
        # Process FilePond upload
        upload_id = self.cleaned_data['upload_id']
        temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)
        
        # Generate UUID-based filename
        file_uuid = uuid.uuid4()
        original_ext = Path(temp_upload.upload_name).suffix.lower()
        secure_filename = f"{file_uuid}{original_ext}"
        
        # Create date-based directory structure: photos/YYYY/MM/originals/
        date_path = timezone.now().strftime('%Y/%m')
        photo_dir = settings.MEDIA_ROOT / f"photos/{date_path}/originals"
        photo_dir.mkdir(parents=True, exist_ok=True)
        destination_path = photo_dir / secure_filename
        
        # Store the upload permanently with relative filename only
        # FilePond will store it in its own storage directory
        stored_upload = store_upload(upload_id, secure_filename)
        
        # Get the actual stored file path from FilePond storage
        stored_file_path = Path(stored_upload.file.path)
        
        # Copy file from FilePond storage to our final destination
        import shutil
        try:
            shutil.copy2(stored_file_path, destination_path)
        except Exception as e:
            raise forms.ValidationError(f"Failed to copy image file: {str(e)}")
        
        # Process image from final destination
        processor = ImageProcessor()
        metadata = processor.get_image_metadata(str(destination_path))
        
        # Generate thumbnail
        thumbnail_dir = photo_dir.parent / 'thumbnails'
        thumbnail_dir.mkdir(exist_ok=True)
        thumbnail_path = thumbnail_dir / f"{file_uuid}_thumb.jpg"
        
        processor.generate_thumbnail(str(destination_path), str(thumbnail_path))
        
        # Set photo fields
        photo.file_id = str(file_uuid)
        photo.original_filename = temp_upload.upload_name
        photo.file_size = metadata.get('size', 0)
        photo.width = metadata.get('width')
        photo.height = metadata.get('height')
        photo.thumbnail_path = str(thumbnail_path.relative_to(settings.MEDIA_ROOT))
        photo.caption = self.cleaned_data.get('caption', '')
        
        if commit:
            photo.save()
        
        return photo


class PhotoSeriesCreateFormNew(BaseEventForm):
    """PhotoSeries form with multiple file upload support."""
    
    upload_ids = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Comma-separated FilePond upload identifiers"
    )
    
    caption = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Legenda da Série"
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
    
    def clean_upload_ids(self):
        upload_ids_str = self.cleaned_data['upload_ids']
        
        if not upload_ids_str:
            raise forms.ValidationError("At least one image must be uploaded")
        
        upload_ids = [uid.strip() for uid in upload_ids_str.split(',') if uid.strip()]
        
        if len(upload_ids) < 1:
            raise forms.ValidationError("At least one image must be uploaded")
        
        # Validate each upload exists
        for upload_id in upload_ids:
            try:
                TemporaryUpload.objects.get(upload_id=upload_id)
            except TemporaryUpload.DoesNotExist:
                raise forms.ValidationError(f"Upload {upload_id} not found or expired")
        
        return upload_ids
    
    def save(self, commit=True):
        photoseries = super().save(commit=False)
        photoseries.caption = self.cleaned_data.get('caption', '')
        
        if commit:
            photoseries.save()
            
            # Process each uploaded image
            upload_ids = self.cleaned_data['upload_ids']
            processor = ImageProcessor()
            
            for order, upload_id in enumerate(upload_ids, start=1):
                temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)
                
                # Generate UUID-based filename
                file_uuid = uuid.uuid4()
                original_ext = Path(temp_upload.upload_name).suffix.lower()
                secure_filename = f"{file_uuid}{original_ext}"
                
                # Create date-based directory structure: photo_series/YYYY/MM/originals/
                date_path = timezone.now().strftime('%Y/%m')
                photo_dir = settings.MEDIA_ROOT / f"photo_series/{date_path}/originals"
                photo_dir.mkdir(parents=True, exist_ok=True)
                destination_path = photo_dir / secure_filename
                
                # Store the upload permanently with relative filename only
                # FilePond will store it in its own storage directory
                stored_upload = store_upload(upload_id, secure_filename)
                
                # Get the actual stored file path from FilePond storage
                stored_file_path = Path(stored_upload.file.path)
                
                # Copy file from FilePond storage to our final destination
                import shutil
                try:
                    shutil.copy2(stored_file_path, destination_path)
                except Exception as e:
                    raise forms.ValidationError(f"Failed to copy image file: {str(e)}")
                
                # Process image from final destination
                metadata = processor.get_image_metadata(str(destination_path))
                
                # Generate thumbnail
                thumbnail_dir = photo_dir.parent / 'thumbnails'
                thumbnail_dir.mkdir(exist_ok=True)
                thumbnail_path = thumbnail_dir / f"{file_uuid}_thumb.jpg"
                processor.generate_thumbnail(str(destination_path), str(thumbnail_path))
                
                # Create PhotoSeriesFile
                PhotoSeriesFile.objects.create(
                    photo_series=photoseries,
                    file_id=str(file_uuid),
                    original_filename=temp_upload.upload_name,
                    file_size=metadata.get('size', 0),
                    width=metadata.get('width'),
                    height=metadata.get('height'),
                    thumbnail_path=str(thumbnail_path.relative_to(settings.MEDIA_ROOT)),
                    order=order
                )
        
        return photoseries


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

    # Multiple file upload field for photo series
    images = MultipleFileField(
        label="Imagens da Série",
        help_text="Selecione múltiplas imagens (JPEG, PNG, WebP). Máximo 5MB por arquivo.",
        widget=MultipleFileInput(attrs={
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
        # The MultipleFileField already handles the file extraction and basic validation
        files = self.cleaned_data.get('images', [])
        
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
    """Simplified VideoClip form using FilePond."""

    upload_id = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="FilePond upload identifier"
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

    def clean_upload_id(self):
        upload_id = self.cleaned_data['upload_id']

        # Validate FilePond upload exists
        try:
            temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)
        except TemporaryUpload.DoesNotExist:
            raise forms.ValidationError("Upload not found or expired")

        # Validate it's a video file
        if not temp_upload.upload_name.lower().endswith(('.mp4', '.mov', '.webm')):
            raise forms.ValidationError("File must be a video")

        return upload_id

    def save(self, commit=True):
        videoclip = super().save(commit=False)

        # Set required fields
        videoclip.patient = self.patient
        videoclip.created_by = self.user
        videoclip.updated_by = self.user
        videoclip.event_type = Event.VIDEO_CLIP_EVENT

        # Process FilePond upload
        upload_id = self.cleaned_data['upload_id']
        temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)

        # Generate UUID-based file path for video storage
        file_uuid = uuid.uuid4()
        original_ext = Path(temp_upload.upload_name).suffix.lower()
        
        # Create date-based directory structure: videos/YYYY/MM/originals/
        date_path = timezone.now().strftime('%Y/%m')
        video_dir = settings.MEDIA_ROOT / f"videos/{date_path}/originals"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate secure filename with UUID
        secure_filename = f"{file_uuid}{original_ext}"
        destination_path = video_dir / secure_filename

        # Store the upload permanently with relative filename only
        # FilePond will store it in its own storage directory
        stored_upload = store_upload(upload_id, secure_filename)
        
        # Get the actual stored file path from FilePond storage
        stored_file_path = Path(stored_upload.file.path)
        
        # Copy file from FilePond storage to our final destination
        import shutil
        try:
            shutil.copy2(stored_file_path, destination_path)
        except Exception as e:
            raise forms.ValidationError(f"Failed to copy video file: {str(e)}")

        # Process video conversion using our final destination file
        processor = VideoProcessor()
        try:
            conversion_result = processor.convert_to_h264(
                str(destination_path),
                str(destination_path)  # Convert in place
            )
        except Exception as e:
            # Clean up the copied file if conversion fails
            if destination_path.exists():
                destination_path.unlink()
            raise forms.ValidationError(f"Video processing failed: {str(e)}")

        # Set videoclip fields using UUID as file_id
        videoclip.file_id = str(file_uuid)
        videoclip.original_filename = temp_upload.upload_name
        videoclip.file_size = conversion_result['converted_size']
        videoclip.duration = int(conversion_result['duration'])
        videoclip.width = conversion_result['width']
        videoclip.height = conversion_result['height']
        videoclip.video_codec = conversion_result['codec']

        if commit:
            videoclip.save()

        return videoclip


class VideoClipCreateFormOld(BaseMediaForm, forms.ModelForm):
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
            
            # Log incoming file size
            print(f"[BACKEND SIZE] Received video file for upload:")
            print(f"  - File name: {video_file.name}")
            print(f"  - File size: {video_file.size:,} bytes ({video_file.size / (1024*1024):.2f} MB)")
            print(f"  - Content type: {video_file.content_type}")
            
            media_file = MediaFile.objects.create_from_upload(video_file)

            # Log processed file size
            print(f"[BACKEND SIZE] MediaFile created successfully:")
            print(f"  - ID: {media_file.id}")
            print(f"  - Original filename: {media_file.original_filename}")
            print(f"  - File size: {media_file.file_size:,} bytes ({media_file.file_size / (1024*1024):.2f} MB)")
            print(f"  - MIME type: {media_file.mime_type}")
            if hasattr(media_file, 'video_codec') and media_file.video_codec:
                print(f"  - Video codec: {media_file.video_codec}")
            if hasattr(media_file, 'duration') and media_file.duration:
                print(f"  - Duration: {media_file.duration} seconds")

            # Associate MediaFile with VideoClip
            video_clip.media_file = media_file
            video_clip.save()
            
            print(f"[BACKEND SIZE] VideoClip saved with ID: {video_clip.id}")

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
        # Extract user parameter if passed (required for consistency with other forms)
        self.user = kwargs.pop('user', None)
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
