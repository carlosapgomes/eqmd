# Phase 1: Complete Video Migration to django-drf-filepond

## Overview

This phase completely removes the current complex video upload implementation and replaces it with django-drf-filepond with server-side H.264 conversion for universal mobile compatibility.

## Key Objectives

- ✅ Remove all current video upload complexity (ffmpeg client-side, compression bundles)
- ✅ Install and configure django-drf-filepond with django-storage
- ✅ Implement server-side video conversion to H.264/MP4
- ✅ Maintain UUID file naming and secure storage structure
- ✅ Ensure universal mobile compatibility (Android/iOS)

## Step 1: Package Installation and Configuration

### Install Required Packages

```bash
uv add django-drf-filepond
uv add django-storages
uv add ffmpeg-python  # For server-side video processing
```

### Add to DJANGO_SETTINGS

```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'django_drf_filepond',
    'storages',
]

# FilePond Configuration
DJANGO_DRF_FILEPOND_UPLOAD_TMP = '/tmp/filepond_uploads'
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = '/tmp/filepond_stored'

# Custom storage for mediafiles with UUID naming
DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'apps.mediafiles.storage.SecureVideoStorage'

# Video processing settings
MEDIA_VIDEO_CONVERSION_ENABLED = True
MEDIA_VIDEO_OUTPUT_FORMAT = 'mp4'
MEDIA_VIDEO_CODEC = 'libx264'
MEDIA_VIDEO_PRESET = 'medium'  # Single quality preset
MEDIA_VIDEO_MAX_DURATION = 120  # 2 minutes
MEDIA_VIDEO_MAX_SIZE = 100 * 1024 * 1024  # 100MB input limit
```

## Step 2: Remove Current Video Implementation

### Files to DELETE completely

```
apps/mediafiles/static/mediafiles/js/videoclip-compression.js
apps/mediafiles/static/mediafiles/js/videoclip-upload.js
apps/mediafiles/static/mediafiles/js/compression/ (entire directory)
static/videoclipCompression-bundle.js
static/videoclipPlayer-bundle.js
```

### Remove from webpack.config.js

```javascript
// DELETE these entries:
videoclipCompression: [
  "./apps/mediafiles/static/mediafiles/js/videoclip-compression.js",
  "./apps/mediafiles/static/mediafiles/css/videoclip.css"
],
videoclipPlayer: [
  "./apps/mediafiles/static/mediafiles/js/videoclip-player.js"
]
```

### Remove from VideoClip templates

- Remove all complex JavaScript initialization
- Remove compression-related template code
- Simplify to basic filepond upload interface

## Step 3: Create Custom Storage Backend

### Create `apps/mediafiles/storage.py`

```python
import os
import uuid
from pathlib import Path
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils import timezone


class SecureVideoStorage(FileSystemStorage):
    """
    Custom storage backend for FilePond that maintains our UUID naming convention
    and secure directory structure.
    """

    def __init__(self):
        # Use our existing media structure
        super().__init__(location=settings.MEDIA_ROOT)

    def _save(self, name, content):
        """
        Save file with UUID naming in structured directory.
        """
        # Generate UUID-based filename
        file_uuid = uuid.uuid4()
        original_ext = Path(name).suffix.lower()

        # Create date-based directory structure: videos/YYYY/MM/originals/
        date_path = timezone.now().strftime('%Y/%m')
        directory = f"videos/{date_path}/originals"

        # Ensure directory exists
        full_dir = os.path.join(self.location, directory)
        os.makedirs(full_dir, exist_ok=True)

        # Generate secure filename
        secure_filename = f"{file_uuid}{original_ext}"
        secure_path = os.path.join(directory, secure_filename)

        # Save the file
        return super()._save(secure_path, content)

    def url(self, name):
        """
        Return secure URL for file access through our view system.
        """
        # Extract UUID from filename for secure URL generation
        filename = Path(name).name
        file_uuid = filename.split('.')[0]  # Get UUID part before extension

        from django.urls import reverse
        return reverse('mediafiles:serve_file', kwargs={'file_id': file_uuid})
```

## Step 4: Server-Side Video Conversion

### Create `apps/mediafiles/video_processor.py`

```python
import os
import tempfile
import ffmpeg
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError


class VideoProcessor:
    """
    Server-side video processing for universal mobile compatibility.
    """

    @staticmethod
    def convert_to_h264(input_path: str, output_path: str) -> dict:
        """
        Convert video to H.264/MP4 for universal mobile compatibility.

        Args:
            input_path: Path to input video file
            output_path: Path for output video file

        Returns:
            dict: Conversion results with metadata
        """
        try:
            # Probe input file
            probe = ffmpeg.probe(input_path)
            video_stream = next((stream for stream in probe['streams']
                               if stream['codec_type'] == 'video'), None)

            if not video_stream:
                raise ValidationError("No video stream found")

            # Check duration limit
            duration = float(video_stream.get('duration', 0))
            max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)
            if duration > max_duration:
                raise ValidationError(f"Video too long: {duration}s > {max_duration}s")

            # Convert to H.264/MP4 with mobile-optimized settings
            (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset='medium',
                    crf=23,  # Good quality for medical content
                    movflags='+faststart',  # Web optimization
                    pix_fmt='yuv420p',  # Universal compatibility
                    vf='scale=trunc(iw/2)*2:trunc(ih/2)*2'  # Ensure even dimensions
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Get output file info
            output_probe = ffmpeg.probe(output_path)
            output_video = next((stream for stream in output_probe['streams']
                               if stream['codec_type'] == 'video'), None)

            return {
                'success': True,
                'original_size': os.path.getsize(input_path),
                'converted_size': os.path.getsize(output_path),
                'duration': duration,
                'width': int(output_video.get('width', 0)),
                'height': int(output_video.get('height', 0)),
                'codec': output_video.get('codec_name', 'h264')
            }

        except Exception as e:
            raise ValidationError(f"Video conversion failed: {str(e)}")

    @staticmethod
    def generate_thumbnail(video_path: str, thumbnail_path: str, time_offset: float = 1.0):
        """
        Generate thumbnail from video at specified time offset.
        """
        try:
            (
                ffmpeg
                .input(video_path, ss=time_offset)
                .output(
                    thumbnail_path,
                    vframes=1,
                    format='image2',
                    vcodec='mjpeg',
                    **{'q:v': 2, 's': '300x300'}
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return True
        except Exception:
            return False
```

## Step 5: Update VideoClip Model and Forms

### Modify `apps/mediafiles/models.py` - VideoClip section

```python
# Remove complex video processing methods from MediaFile
# Keep only basic metadata extraction

class VideoClip(Event):
    """Simplified VideoClip model using FilePond."""

    # Remove media_file OneToOneField - will be handled by FilePond
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

    duration = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Duração em segundos"
    )

    # ... other fields remain the same
```

### Create new `apps/mediafiles/forms.py` - VideoClip form

```python
from django_drf_filepond.models import TemporaryUpload
from django_drf_filepond.api import store_upload

class VideoClipCreateForm(BaseEventForm):
    """Simplified VideoClip form using FilePond."""

    upload_id = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="FilePond upload identifier"
    )

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

        # Process FilePond upload
        upload_id = self.cleaned_data['upload_id']
        temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)

        # Store the upload permanently and get file info
        stored_upload = store_upload(upload_id, destination_file_name=None)

        # Process video conversion
        processor = VideoProcessor()
        conversion_result = processor.convert_to_h264(
            stored_upload.file.path,
            stored_upload.file.path  # Convert in place
        )

        # Set videoclip fields
        videoclip.file_id = stored_upload.upload_id
        videoclip.original_filename = temp_upload.upload_name
        videoclip.file_size = conversion_result['converted_size']
        videoclip.duration = int(conversion_result['duration'])

        if commit:
            videoclip.save()

        return videoclip
```

## Step 6: Update Templates

### Create new `apps/mediafiles/templates/mediafiles/videoclip_form.html`

```html
{% extends "base.html" %} {% load static %} {% block title %} {% if is_update
%}Editar Vídeo{% else %}Adicionar Vídeo{% endif %} - {{ patient.name }} {%
endblock %} {% block extra_css %}
<link href="https://unpkg.com/filepond/dist/filepond.css" rel="stylesheet" />
<link
  href="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css"
  rel="stylesheet"
/>
{% endblock %} {% block content %}
<div class="container mt-4">
  <div class="row justify-content-center">
    <div class="col-md-8">
      <div class="card">
        <div class="card-header">
          <h5 class="mb-0">
            {% if is_update %}Editar Vídeo{% else %}Adicionar Vídeo{% endif %} -
            {{ patient.name }}
          </h5>
        </div>
        <div class="card-body">
          <form method="post" enctype="multipart/form-data">
            {% csrf_token %}

            <!-- FilePond Upload Area -->
            {% if not is_update %}
            <div class="mb-3">
              <label class="form-label">Arquivo de Vídeo</label>
              <input
                type="file"
                class="filepond"
                name="video"
                accept="video/*"
                data-max-file-size="100MB"
                data-max-files="1"
              />
              <div class="form-text">
                Formatos aceitos: MP4, MOV, WebM. Máximo 2 minutos, 100MB. O
                vídeo será convertido automaticamente para compatibilidade
                mobile.
              </div>
            </div>
            {% endif %}

            <!-- Form fields -->
            {{ form.as_p }}

            <div class="d-flex justify-content-between">
              <a
                href="{{ patient.get_timeline_url }}"
                class="btn btn-secondary"
              >
                <i class="bi bi-arrow-left"></i> Voltar
              </a>
              <button type="submit" class="btn btn-primary">
                <i class="bi bi-save"></i>
                {% if is_update %}Atualizar{% else %}Adicionar{% endif %} Vídeo
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %} {% block extra_js %}
<script src="https://unpkg.com/filepond/dist/filepond.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-size/dist/filepond-plugin-file-validate-size.js"></script>

<script>
  // Register FilePond plugins
  FilePond.registerPlugin(
    FilePondPluginFileValidateType,
    FilePondPluginFileValidateSize,
  );

  // Initialize FilePond
  const inputElement = document.querySelector(".filepond");
  if (inputElement) {
    const pond = FilePond.create(inputElement, {
      server: {
        process: "/fp/process/",
        revert: "/fp/revert/",
        restore: "/fp/restore/",
        load: "/fp/load/",
        fetch: "/fp/fetch/",
      },
      acceptedFileTypes: [
        "video/mp4",
        "video/mov",
        "video/webm",
        "video/quicktime",
      ],
      maxFileSize: "100MB",
      maxFiles: 1,
      allowMultiple: false,
      labelIdle:
        'Arraste o vídeo aqui ou <span class="filepond--label-action">procure</span>',
      labelFileProcessing: "Processando...",
      labelFileProcessingComplete: "Processamento concluído",
      labelFileProcessingAborted: "Processamento cancelado",
      labelFileProcessingError: "Erro no processamento",
      labelFileWaitingForSize: "Aguardando tamanho",
      labelFileSizeNotAvailable: "Tamanho não disponível",
      onprocessfile: (error, file) => {
        if (!error) {
          // Set the upload ID in the hidden form field
          document.querySelector('input[name="upload_id"]').value =
            file.serverId;
        }
      },
    });
  }
</script>
{% endblock %}
```

## Step 7: Update URL Configuration

### Update `apps/mediafiles/urls.py`

```python
from django.urls import path, include

app_name = 'mediafiles'

urlpatterns = [
    # FilePond URLs
    path('fp/', include('django_drf_filepond.urls')),

    # Existing URLs remain the same
    # ...
]
```

## Step 8: Run Migrations and Tests

### Create and run migrations

```bash
python manage.py makemigrations mediafiles
python manage.py migrate
```

### Test video upload

1. Create a new VideoClip for a patient
2. Upload a test video file (MP4, MOV, or WebM)
3. Verify server-side conversion to H.264
4. Test playback on mobile devices (Android Chrome, iOS Safari)
5. Verify timeline integration still works

## Success Criteria

- ✅ Video uploads work reliably without client-side compression
- ✅ All videos automatically converted to H.264/MP4
- ✅ Mobile compatibility confirmed (Android/iOS)
- ✅ UUID file naming maintained
- ✅ Secure file serving still works
- ✅ Timeline integration functional
- ✅ No JavaScript bundle errors
- ✅ Simplified codebase with removed complexity

## Next Phase

Once Phase 1 is complete and tested, proceed to Phase 2 for Photo and PhotoSeries migration.
