# Phase 2: Photo and PhotoSeries Migration to django-drf-filepond

## Overview
This phase migrates Photo and PhotoSeries functionality to use django-drf-filepond, maintaining the multiple file upload capability for PhotoSeries while simplifying the JavaScript architecture and eliminating webpack bundle complexity.

## Prerequisites
- Phase 1 (Video migration) must be completed successfully
- django-drf-filepond configured and working for videos
- Server-side processing pipeline established

## Key Objectives
- ✅ Migrate Photo model to use FilePond uploads
- ✅ Migrate PhotoSeries with multiple file support
- ✅ Simplify JavaScript bundles and eliminate complex webpack config
- ✅ Update timeline integration for new upload system
- ✅ Maintain UUID file naming and secure storage

## Step 1: Extend Storage Backend for Images

### Update `apps/mediafiles/storage.py`:
```python
class SecureImageStorage(FileSystemStorage):
    """
    Custom storage backend for image files with UUID naming.
    """
    
    def __init__(self):
        super().__init__(location=settings.MEDIA_ROOT)
    
    def _save(self, name, content):
        """Save image file with UUID naming in structured directory."""
        file_uuid = uuid.uuid4()
        original_ext = Path(name).suffix.lower()
        
        # Determine if it's a single photo or part of a series
        # This will be handled by the upload context
        upload_type = getattr(content, '_upload_type', 'photos')  # Default to photos
        
        # Create date-based directory structure
        date_path = timezone.now().strftime('%Y/%m')
        directory = f"{upload_type}/{date_path}/originals"
        
        # Ensure directory exists
        full_dir = os.path.join(self.location, directory)
        os.makedirs(full_dir, exist_ok=True)
        
        # Generate secure filename
        secure_filename = f"{file_uuid}{original_ext}"
        secure_path = os.path.join(directory, secure_filename)
        
        return super()._save(secure_path, content)


class SecurePhotoSeriesStorage(SecureImageStorage):
    """
    Storage backend specifically for photo series.
    """
    
    def _save(self, name, content):
        # Mark content as photo series type
        content._upload_type = 'photo_series'
        return super()._save(name, content)
```

### Update settings.py:
```python
# Add image storage configurations
DJANGO_DRF_FILEPOND_STORAGES_BACKEND_PHOTO = 'apps.mediafiles.storage.SecureImageStorage'
DJANGO_DRF_FILEPOND_STORAGES_BACKEND_PHOTOSERIES = 'apps.mediafiles.storage.SecurePhotoSeriesStorage'

# Image processing settings
MEDIA_IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5MB
MEDIA_ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MEDIA_THUMBNAIL_SIZE = (300, 300)
```

## Step 2: Create Image Processor

### Create `apps/mediafiles/image_processor.py`:
```python
import os
from pathlib import Path
from PIL import Image
from django.conf import settings


class ImageProcessor:
    """
    Server-side image processing for thumbnails and optimization.
    """
    
    @staticmethod
    def generate_thumbnail(image_path: str, thumbnail_path: str) -> bool:
        """
        Generate thumbnail for image file.
        
        Args:
            image_path: Path to original image
            thumbnail_path: Path for thumbnail
            
        Returns:
            bool: Success status
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                thumbnail_size = getattr(settings, 'MEDIA_THUMBNAIL_SIZE', (300, 300))
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                return True
                
        except Exception as e:
            print(f"Thumbnail generation failed: {e}")
            return False
    
    @staticmethod
    def get_image_metadata(image_path: str) -> dict:
        """
        Extract image metadata.
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size': os.path.getsize(image_path)
                }
        except Exception:
            return {}
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """
        Validate image file integrity.
        """
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False
```

## Step 3: Update Photo Model and Forms

### Modify `apps/mediafiles/models.py` - Photo section:
```python
class Photo(Event):
    """Simplified Photo model using FilePond."""
    
    # Replace media_file with FilePond fields
    file_id = models.CharField(
        max_length=100,
        verbose_name="File ID",
        help_text="FilePond file identifier"
    )
    
    original_filename = models.CharField(
        max_length=255,
        verbose_name="Nome Original"
    )
    
    file_size = models.PositiveIntegerField(
        verbose_name="Tamanho do Arquivo"
    )
    
    width = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Largura"
    )
    
    height = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Altura"
    )
    
    thumbnail_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Caminho da Miniatura"
    )
    
    # Keep existing fields
    caption = models.TextField(
        blank=True,
        verbose_name="Legenda"
    )
    
    def get_secure_url(self):
        """Return secure file URL."""
        from django.urls import reverse
        return reverse('mediafiles:serve_file', kwargs={'file_id': self.file_id})
    
    def get_thumbnail_url(self):
        """Return thumbnail URL."""
        if self.thumbnail_path:
            from django.urls import reverse
            return reverse('mediafiles:serve_thumbnail', kwargs={'file_id': self.file_id})
        return None


# Remove MediaFile model dependencies from Photo
```

### Create new `apps/mediafiles/forms.py` - Photo form:
```python
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond.api import store_upload

class PhotoCreateForm(BaseEventForm):
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
        
        # Store the upload permanently
        stored_upload = store_upload(upload_id, destination_file_name=None)
        
        # Process image
        processor = ImageProcessor()
        metadata = processor.get_image_metadata(stored_upload.file.path)
        
        # Generate thumbnail
        thumbnail_dir = Path(stored_upload.file.path).parent.parent / 'thumbnails'
        thumbnail_dir.mkdir(exist_ok=True)
        thumbnail_path = thumbnail_dir / f"{Path(stored_upload.file.path).stem}_thumb.jpg"
        
        processor.generate_thumbnail(stored_upload.file.path, str(thumbnail_path))
        
        # Set photo fields
        photo.file_id = stored_upload.upload_id
        photo.original_filename = temp_upload.upload_name
        photo.file_size = metadata.get('size', 0)
        photo.width = metadata.get('width')
        photo.height = metadata.get('height')
        photo.thumbnail_path = str(thumbnail_path.relative_to(settings.MEDIA_ROOT))
        photo.caption = self.cleaned_data.get('caption', '')
        
        if commit:
            photo.save()
        
        return photo
```

## Step 4: Update PhotoSeries Model and Forms

### Modify PhotoSeries model:
```python
class PhotoSeries(Event):
    """PhotoSeries model using FilePond for multiple uploads."""
    
    caption = models.TextField(
        blank=True,
        verbose_name="Legenda da Série"
    )
    
    def get_photos(self):
        """Return related PhotoSeriesFile objects."""
        return self.photoseriesfile_set.all().order_by('order')
    
    def get_photo_count(self):
        """Return number of photos in series."""
        return self.photoseriesfile_set.count()
    
    def get_primary_thumbnail(self):
        """Return first photo thumbnail."""
        first_photo = self.get_photos().first()
        if first_photo:
            return first_photo.get_thumbnail_url()
        return None


class PhotoSeriesFile(models.Model):
    """Individual photo within a series."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    photo_series = models.ForeignKey(PhotoSeries, on_delete=models.CASCADE)
    
    file_id = models.CharField(max_length=100, verbose_name="File ID")
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    thumbnail_path = models.CharField(max_length=500, blank=True)
    
    order = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        unique_together = [['photo_series', 'order']]
    
    def get_secure_url(self):
        from django.urls import reverse
        return reverse('mediafiles:serve_file', kwargs={'file_id': self.file_id})
    
    def get_thumbnail_url(self):
        if self.thumbnail_path:
            from django.urls import reverse
            return reverse('mediafiles:serve_thumbnail', kwargs={'file_id': self.file_id})
        return None
```

### Create PhotoSeries form:
```python
class PhotoSeriesCreateForm(BaseEventForm):
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
                stored_upload = store_upload(upload_id, destination_file_name=None)
                
                # Process image
                metadata = processor.get_image_metadata(stored_upload.file.path)
                
                # Generate thumbnail
                thumbnail_dir = Path(stored_upload.file.path).parent.parent / 'thumbnails'
                thumbnail_dir.mkdir(exist_ok=True)
                thumbnail_path = thumbnail_dir / f"{Path(stored_upload.file.path).stem}_thumb.jpg"
                processor.generate_thumbnail(stored_upload.file.path, str(thumbnail_path))
                
                # Create PhotoSeriesFile
                PhotoSeriesFile.objects.create(
                    photo_series=photoseries,
                    file_id=stored_upload.upload_id,
                    original_filename=temp_upload.upload_name,
                    file_size=metadata.get('size', 0),
                    width=metadata.get('width'),
                    height=metadata.get('height'),
                    thumbnail_path=str(thumbnail_path.relative_to(settings.MEDIA_ROOT)),
                    order=order
                )
        
        return photoseries
```

## Step 5: Update Templates

### Create `apps/mediafiles/templates/mediafiles/photo_form.html`:
```html
{% extends "base.html" %}
{% load static %}

{% block title %}
  {% if is_update %}Editar Foto{% else %}Adicionar Foto{% endif %} - {{ patient.name }}
{% endblock %}

{% block extra_css %}
<link href="https://unpkg.com/filepond/dist/filepond.css" rel="stylesheet">
<link href="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        {% if is_update %}Editar Foto{% else %}Adicionar Foto{% endif %}
                        - {{ patient.name }}
                    </h5>
                </div>
                <div class="card-body">
                    <form method="post" enctype="multipart/form-data">
                        {% csrf_token %}
                        
                        {% if not is_update %}
                        <div class="mb-3">
                            <label class="form-label">Arquivo de Imagem</label>
                            <input type="file" 
                                   class="filepond" 
                                   name="image"
                                   accept="image/*"
                                   data-max-file-size="5MB"
                                   data-max-files="1">
                            <div class="form-text">
                                Formatos aceitos: JPEG, PNG, WebP. Máximo 5MB.
                            </div>
                        </div>
                        {% endif %}
                        
                        {{ form.as_p }}
                        
                        <div class="d-flex justify-content-between">
                            <a href="{{ patient.get_timeline_url }}" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Voltar
                            </a>
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-save"></i>
                                {% if is_update %}Atualizar{% else %}Adicionar{% endif %} Foto
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://unpkg.com/filepond/dist/filepond.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-size/dist/filepond-plugin-file-validate-size.js"></script>
<script src="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.js"></script>

<script>
// Register FilePond plugins
FilePond.registerPlugin(
    FilePondPluginFileValidateType,
    FilePondPluginFileValidateSize,
    FilePondPluginImagePreview
);

// Initialize FilePond
const inputElement = document.querySelector('.filepond');
if (inputElement) {
    const pond = FilePond.create(inputElement, {
        server: {
            process: '/fp/process/',
            revert: '/fp/revert/',
            restore: '/fp/restore/',
            load: '/fp/load/',
            fetch: '/fp/fetch/'
        },
        acceptedFileTypes: ['image/jpeg', 'image/png', 'image/webp'],
        maxFileSize: '5MB',
        maxFiles: 1,
        allowMultiple: false,
        imagePreviewHeight: 170,
        labelIdle: 'Arraste a imagem aqui ou <span class="filepond--label-action">procure</span>',
        onprocessfile: (error, file) => {
            if (!error) {
                document.querySelector('input[name="upload_id"]').value = file.serverId;
            }
        }
    });
}
</script>
{% endblock %}
```

### Create `apps/mediafiles/templates/mediafiles/photoseries_create.html`:
```html
{% extends "base.html" %}
{% load static %}

{% block title %}Adicionar Série de Fotos - {{ patient.name }}{% endblock %}

{% block extra_css %}
<link href="https://unpkg.com/filepond/dist/filepond.css" rel="stylesheet">
<link href="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-10">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Adicionar Série de Fotos - {{ patient.name }}</h5>
                </div>
                <div class="card-body">
                    <form method="post" enctype="multipart/form-data">
                        {% csrf_token %}
                        
                        <div class="mb-3">
                            <label class="form-label">Imagens da Série</label>
                            <input type="file" 
                                   class="filepond" 
                                   name="images"
                                   accept="image/*"
                                   multiple
                                   data-max-file-size="5MB"
                                   data-max-files="20">
                            <div class="form-text">
                                Selecione múltiplas imagens para criar uma série. 
                                Formatos aceitos: JPEG, PNG, WebP. Máximo 5MB por imagem.
                            </div>
                        </div>
                        
                        {{ form.as_p }}
                        
                        <div class="d-flex justify-content-between">
                            <a href="{{ patient.get_timeline_url }}" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Voltar
                            </a>
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-save"></i> Criar Série de Fotos
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://unpkg.com/filepond/dist/filepond.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-size/dist/filepond-plugin-file-validate-size.js"></script>
<script src="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.js"></script>

<script>
// Register FilePond plugins
FilePond.registerPlugin(
    FilePondPluginFileValidateType,
    FilePondPluginFileValidateSize,
    FilePondPluginImagePreview
);

// Initialize FilePond for multiple files
const inputElement = document.querySelector('.filepond');
if (inputElement) {
    const pond = FilePond.create(inputElement, {
        server: {
            process: '/fp/process/',
            revert: '/fp/revert/',
            restore: '/fp/restore/',
            load: '/fp/load/',
            fetch: '/fp/fetch/'
        },
        acceptedFileTypes: ['image/jpeg', 'image/png', 'image/webp'],
        maxFileSize: '5MB',
        maxFiles: 20,
        allowMultiple: true,
        allowReorder: true,
        imagePreviewHeight: 170,
        labelIdle: 'Arraste as imagens aqui ou <span class="filepond--label-action">procure</span>',
        onprocessfiles: () => {
            // Collect all processed file IDs
            const uploadIds = pond.getFiles()
                .filter(file => file.status === FilePond.FileStatus.PROCESSING_COMPLETE)
                .map(file => file.serverId)
                .join(',');
            
            document.querySelector('input[name="upload_ids"]').value = uploadIds;
        }
    });
}
</script>
{% endblock %}
```

## Step 6: Remove Legacy JavaScript and Webpack Complexity

### Files to DELETE:
```
apps/mediafiles/static/mediafiles/js/photo.js
apps/mediafiles/static/mediafiles/js/photoseries.js
apps/mediafiles/static/mediafiles/js/image-processing.js
apps/mediafiles/static/mediafiles/js/mediafiles.js
static/photo-bundle.js
static/photoseries-bundle.js
static/mediafiles-bundle.js
static/image-processing-*-bundle.js
```

### Simplify webpack.config.js:
```javascript
module.exports = {
  entry: {
    main: [
      "./assets/index.js", 
      "./assets/scss/main.scss",
      "./apps/events/static/events/js/timeline.js",
      "./apps/events/static/events/js/accessibility.js"
    ]
    // Remove all mediafiles entries - now using CDN FilePond
  },
  // ... rest of config simplified
  optimization: {
    // Remove complex splitChunks - much simpler now
    minimizer: [`...`, new CssMinimizerPlugin()],
    minimize: true
  }
};
```

## Step 7: Update Timeline Integration

### Update event card templates to work without complex JS:
```html
<!-- apps/events/templates/events/partials/event_card_photo.html -->
<div class="event-card" data-event-type="photo">
    <div class="event-header">
        <h6 class="event-title">📷 Foto</h6>
        <small class="text-muted">{{ photo.event_datetime|date:"d/m/Y H:i" }}</small>
    </div>
    <div class="event-content">
        <div class="photo-preview">
            <img src="{{ photo.get_thumbnail_url }}" 
                 alt="{{ photo.original_filename }}"
                 class="img-thumbnail"
                 style="max-height: 150px; cursor: pointer;"
                 onclick="showPhotoModal('{{ photo.get_secure_url }}', '{{ photo.original_filename }}')">
        </div>
        {% if photo.caption %}
        <p class="mt-2 mb-0">{{ photo.caption }}</p>
        {% endif %}
    </div>
</div>

<script>
function showPhotoModal(imageUrl, filename) {
    // Simple modal without complex JS
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${filename}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="${imageUrl}" class="img-fluid" alt="${filename}">
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    new bootstrap.Modal(modal).show();
    modal.addEventListener('hidden.bs.modal', () => modal.remove());
}
</script>
```

## Step 8: Run Migrations and Tests

### Create and run migrations:
```bash
python manage.py makemigrations mediafiles
python manage.py migrate
```

### Test complete photo workflow:
1. Upload single photo - verify FilePond upload works
2. Upload photo series - verify multiple file support
3. Test timeline display of both photo types
4. Verify thumbnails are generated correctly
5. Test mobile upload experience
6. Verify secure file serving still works

## Success Criteria
- ✅ Photo uploads work with FilePond (single file)
- ✅ PhotoSeries uploads work with FilePond (multiple files)
- ✅ Timeline integration displays photos correctly
- ✅ Thumbnails generated automatically
- ✅ Mobile upload experience improved
- ✅ JavaScript complexity eliminated
- ✅ Webpack configuration simplified
- ✅ No bundle loading errors
- ✅ UUID file naming maintained
- ✅ Secure file serving functional

## Next Phase
Once Phase 2 is complete and tested, proceed to Phase 3 for final cleanup and optimization.