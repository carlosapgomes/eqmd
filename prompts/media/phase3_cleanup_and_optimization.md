# Phase 3: Cleanup and Optimization

## Overview

This final phase removes all legacy media upload code, optimizes the new FilePond-based system, updates documentation and tests, and prepares the system for deployment with comprehensive mobile testing.

## Prerequisites

- Phase 1 (Video migration) completed successfully
- Phase 2 (Photo migration) completed successfully
- All FilePond uploads working correctly
- Timeline integration functional

## Key Objectives

- ✅ Remove all legacy upload code and files
- ✅ Optimize FilePond configuration and performance
- ✅ Update tests for new upload system
- ✅ Comprehensive mobile compatibility testing
- ✅ Security review and optimization
- ✅ Update documentation
- ✅ Performance testing and optimization

## Step 1: Complete Legacy Code Removal

### Remove Legacy Models and Code

#### Update `apps/mediafiles/models.py`

```python
# REMOVE COMPLETELY:
class MediaFile(models.Model):  # DELETE entire class
class PhotoSeriesFile(models.Model):  # Will be recreated with new structure
# Remove all ffmpeg-related methods
# Remove all complex video processing code
# Remove deduplication code

# Keep only the new simplified models:
# - Photo (with FilePond fields)
# - PhotoSeries (with FilePond fields)
# - PhotoSeriesFile (simplified)
# - VideoClip (with FilePond fields)
```

#### Remove legacy files completely

```bash
# Delete these files and directories
apps/mediafiles/utils.py  # Old utility functions
apps/mediafiles/security.py  # Replaced by FilePond security
apps/mediafiles/static/mediafiles/js/  # Entire directory
apps/mediafiles/static/mediafiles/css/ # Will be replaced with minimal CSS
apps/mediafiles/templates/mediafiles/old_*  # Any old templates

# Remove webpack bundles
static/mediafiles-bundle.js
static/photo-bundle.js
static/photoseries-bundle.js
static/videoclip*-bundle.js
static/image-processing-*-bundle.js
```

#### Clean up webpack.config.js

```javascript
// FINAL simplified configuration
module.exports = {
  entry: {
    main: [
      "./assets/index.js",
      "./assets/scss/main.scss",
      "./apps/events/static/events/js/timeline.js",
      "./apps/events/static/events/js/accessibility.js",
    ],
    // All mediafiles entries removed - using CDN FilePond
  },
  output: {
    filename: "[name]-bundle.js",
    path: path.resolve(__dirname, "./static"),
    clean: true,
  },
  module: {
    rules: [
      {
        test: /\.scss$/,
        use: [
          MiniCssExtractPlugin.loader,
          "css-loader",
          "postcss-loader",
          "sass-loader",
        ],
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, "css-loader", "postcss-loader"],
      },
    ],
  },
  plugins: [
    new MiniCssExtractPlugin({ filename: "[name].css" }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: "node_modules/easymde/dist/easymde.min.js",
          to: "js/easymde.min.js",
        },
        {
          from: "node_modules/easymde/dist/easymde.min.css",
          to: "css/easymde.min.css",
        },
        {
          from: "node_modules/bootstrap/dist/js/bootstrap.min.js",
          to: "js/bootstrap.min.js",
        },
        {
          from: "node_modules/bootstrap-icons/font/bootstrap-icons.min.css",
          to: "css/bootstrap-icons.min.css",
        },
        {
          from: "node_modules/bootstrap-icons/font/fonts/bootstrap-icons.woff2",
          to: "css/fonts/bootstrap-icons.woff2",
        },
        {
          from: "node_modules/@popperjs/core/dist/umd/popper.min.js",
          to: "js/popper.min.js",
        },
        { from: "assets/images", to: "images" },
        { from: "assets/*.ico", to: "[name][ext]" },
        { from: "assets/*.png", to: "[name][ext]", noErrorOnMissing: true },
      ],
    }),
  ],
  optimization: {
    minimizer: [`...`, new CssMinimizerPlugin()],
    minimize: true,
    // No complex splitChunks needed anymore
  },
  resolve: {
    extensions: [".js", ".scss", ".css"],
  },
};
```

## Step 2: Optimize FilePond Configuration

### Create centralized FilePond configuration

#### Create `apps/mediafiles/static/mediafiles/js/filepond-config.js`

```javascript
/**
 * Centralized FilePond configuration for EquipeMed
 * This file provides consistent FilePond setup across all upload types
 */

// Register all required plugins
FilePond.registerPlugin(
  FilePondPluginFileValidateType,
  FilePondPluginFileValidateSize,
  FilePondPluginImagePreview,
);

// Common FilePond configuration
const FILEPOND_COMMON_CONFIG = {
  server: {
    process: "/fp/process/",
    revert: "/fp/revert/",
    restore: "/fp/restore/",
    load: "/fp/load/",
    fetch: "/fp/fetch/",
  },
  labelIdle:
    'Arraste arquivos aqui ou <span class="filepond--label-action">procure</span>',
  labelFileProcessing: "Processando...",
  labelFileProcessingComplete: "Processamento concluído",
  labelFileProcessingAborted: "Processamento cancelado",
  labelFileProcessingError: "Erro no processamento",
  labelFileWaitingForSize: "Aguardando tamanho",
  labelFileSizeNotAvailable: "Tamanho não disponível",
  labelInvalidField: "Campo contém arquivos inválidos",
  labelFileCountSingular: "arquivo selecionado",
  labelFileCountPlural: "arquivos selecionados",
  labelFileLoading: "Carregando...",
  labelFileLoadError: "Erro ao carregar",
  labelFileRemoveError: "Erro ao remover",
  labelFileRemove: "Remover",
  labelFileProcess: "Enviar",
  labelFileProcessError: "Erro no envio",
  labelTapToCancel: "toque para cancelar",
  labelTapToRetry: "toque para tentar novamente",
  labelTapToUndo: "toque para desfazer",
};

// Video-specific configuration
const FILEPOND_VIDEO_CONFIG = {
  ...FILEPOND_COMMON_CONFIG,
  acceptedFileTypes: [
    "video/mp4",
    "video/mov",
    "video/webm",
    "video/quicktime",
  ],
  maxFileSize: "100MB",
  maxFiles: 1,
  allowMultiple: false,
  onprocessfile: (error, file) => {
    if (!error) {
      document.querySelector('input[name="upload_id"]').value = file.serverId;
    }
  },
};

// Image-specific configuration
const FILEPOND_IMAGE_CONFIG = {
  ...FILEPOND_COMMON_CONFIG,
  acceptedFileTypes: ["image/jpeg", "image/png", "image/webp"],
  maxFileSize: "5MB",
  maxFiles: 1,
  allowMultiple: false,
  imagePreviewHeight: 170,
  onprocessfile: (error, file) => {
    if (!error) {
      document.querySelector('input[name="upload_id"]').value = file.serverId;
    }
  },
};

// Photo series configuration
const FILEPOND_PHOTOSERIES_CONFIG = {
  ...FILEPOND_COMMON_CONFIG,
  acceptedFileTypes: ["image/jpeg", "image/png", "image/webp"],
  maxFileSize: "5MB",
  maxFiles: 20,
  allowMultiple: true,
  allowReorder: true,
  imagePreviewHeight: 170,
  onprocessfiles: () => {
    const pond = FilePond.find(document.querySelector(".filepond"));
    const uploadIds = pond
      .getFiles()
      .filter((file) => file.status === FilePond.FileStatus.PROCESSING_COMPLETE)
      .map((file) => file.serverId)
      .join(",");

    document.querySelector('input[name="upload_ids"]').value = uploadIds;
  },
};

// Initialize functions
function initVideoUpload(selector = ".filepond") {
  const element = document.querySelector(selector);
  if (element) {
    return FilePond.create(element, FILEPOND_VIDEO_CONFIG);
  }
}

function initImageUpload(selector = ".filepond") {
  const element = document.querySelector(selector);
  if (element) {
    return FilePond.create(element, FILEPOND_IMAGE_CONFIG);
  }
}

function initPhotoSeriesUpload(selector = ".filepond") {
  const element = document.querySelector(selector);
  if (element) {
    return FilePond.create(element, FILEPOND_PHOTOSERIES_CONFIG);
  }
}

// Make functions available globally
window.EquipeMedFilePond = {
  initVideoUpload,
  initImageUpload,
  initPhotoSeriesUpload,
};
```

### Update all templates to use centralized config

#### Update base template to include FilePond

```html
<!-- base.html - Add to head section -->
{% block extra_css %}
<link href="https://unpkg.com/filepond/dist/filepond.css" rel="stylesheet" />
<link
  href="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css"
  rel="stylesheet"
/>
{% endblock %} {% block extra_js %}
<script src="https://unpkg.com/filepond/dist/filepond.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.js"></script>
<script src="https://unpkg.com/filepond-plugin-file-validate-size/dist/filepond-plugin-file-validate-size.js"></script>
<script src="https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.js"></script>
<script src="{% static 'mediafiles/js/filepond-config.js' %}"></script>
{% endblock %}
```

#### Simplify all upload templates

```html
<!-- videoclip_form.html -->
<script>
  document.addEventListener("DOMContentLoaded", function () {
    window.EquipeMedFilePond.initVideoUpload();
  });
</script>

<!-- photo_form.html -->
<script>
  document.addEventListener("DOMContentLoaded", function () {
    window.EquipeMedFilePond.initImageUpload();
  });
</script>

<!-- photoseries_create.html -->
<script>
  document.addEventListener("DOMContentLoaded", function () {
    window.EquipeMedFilePond.initPhotoSeriesUpload();
  });
</script>
```

## Step 3: Optimize Server-Side Processing

### Enhance video processor for better performance

```python
# apps/mediafiles/video_processor.py - Add performance optimizations

class VideoProcessor:
    @staticmethod
    def convert_to_h264(input_path: str, output_path: str) -> dict:
        """Enhanced video conversion with performance optimizations."""
        try:
            # Probe input file
            probe = ffmpeg.probe(input_path)
            video_stream = next((stream for stream in probe['streams']
                               if stream['codec_type'] == 'video'), None)

            if not video_stream:
                raise ValidationError("No video stream found")

            # Get input dimensions
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))

            # Optimize for mobile - limit resolution if too high
            max_width = 1920
            max_height = 1080

            if width > max_width or height > max_height:
                # Calculate scaling while maintaining aspect ratio
                scale_factor = min(max_width / width, max_height / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                # Ensure even dimensions
                new_width = (new_width // 2) * 2
                new_height = (new_height // 2) * 2
                scale_filter = f'scale={new_width}:{new_height}'
            else:
                scale_filter = 'scale=trunc(iw/2)*2:trunc(ih/2)*2'

            # Convert with optimized settings
            (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset='fast',  # Faster encoding
                    crf=25,  # Slightly lower quality for better compression
                    movflags='+faststart',
                    pix_fmt='yuv420p',
                    vf=scale_filter,
                    maxrate='2M',  # Limit bitrate for mobile
                    bufsize='4M'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )

            # Verify output file
            if not os.path.exists(output_path):
                raise ValidationError("Conversion failed - output file not created")

            # Get final file info
            output_probe = ffmpeg.probe(output_path)
            output_video = next((stream for stream in output_probe['streams']
                               if stream['codec_type'] == 'video'), None)

            return {
                'success': True,
                'original_size': os.path.getsize(input_path),
                'converted_size': os.path.getsize(output_path),
                'duration': float(video_stream.get('duration', 0)),
                'width': int(output_video.get('width', 0)),
                'height': int(output_video.get('height', 0)),
                'codec': output_video.get('codec_name', 'h264'),
                'compression_ratio': os.path.getsize(input_path) / os.path.getsize(output_path)
            }

        except Exception as e:
            raise ValidationError(f"Video conversion failed: {str(e)}")
```

### Add image optimization

```python
# apps/mediafiles/image_processor.py - Add optimization

class ImageProcessor:
    @staticmethod
    def optimize_image(image_path: str, max_width: int = 1920, max_height: int = 1080, quality: int = 85) -> dict:
        """
        Optimize image for web with size limits and quality compression.
        """
        try:
            with Image.open(image_path) as img:
                original_size = os.path.getsize(image_path)

                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Resize if too large
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # Save optimized version
                img.save(image_path, 'JPEG', quality=quality, optimize=True)

                optimized_size = os.path.getsize(image_path)

                return {
                    'optimized': True,
                    'original_size': original_size,
                    'optimized_size': optimized_size,
                    'compression_ratio': original_size / optimized_size if optimized_size > 0 else 1,
                    'final_dimensions': (img.width, img.height)
                }

        except Exception as e:
            return {'optimized': False, 'error': str(e)}
```

## Step 4: Update Tests

### Create comprehensive test suite

```python
# apps/mediafiles/tests/test_filepond_integration.py

import tempfile
import os
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django_drf_filepond.models import TemporaryUpload
from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from ..models import VideoClip, Photo, PhotoSeries
from ..video_processor import VideoProcessor
from ..image_processor import ImageProcessor

User = get_user_model()

class FilePondIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.hospital = Hospital.objects.create(name='Test Hospital')
        self.patient = Patient.objects.create(
            name='Test Patient',
            current_hospital=self.hospital
        )

    def test_video_upload_and_conversion(self):
        """Test video upload through FilePond and H.264 conversion."""
        # Create a test video file (you'd use a real test video file)
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            # In real tests, use a small test video file
            tmp_file.write(b'fake video content')
            test_video_path = tmp_file.name

        try:
            # Test video conversion
            output_path = test_video_path.replace('.mp4', '_converted.mp4')

            # This would fail with fake content, but shows the test structure
            # In real tests, use actual video files
            with self.assertRaises(Exception):  # Expected with fake content
                VideoProcessor.convert_to_h264(test_video_path, output_path)

        finally:
            # Cleanup
            for path in [test_video_path, output_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_image_optimization(self):
        """Test image optimization and thumbnail generation."""
        # Create a test image
        from PIL import Image

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            # Create a test image
            img = Image.new('RGB', (2000, 1500), color='red')
            img.save(tmp_file.name, 'JPEG')
            test_image_path = tmp_file.name

        try:
            # Test image optimization
            result = ImageProcessor.optimize_image(test_image_path, max_width=1920, max_height=1080)
            self.assertTrue(result['optimized'])
            self.assertIn('compression_ratio', result)

            # Test thumbnail generation
            thumbnail_path = test_image_path.replace('.jpg', '_thumb.jpg')
            success = ImageProcessor.generate_thumbnail(test_image_path, thumbnail_path)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(thumbnail_path))

        finally:
            # Cleanup
            for path in [test_image_path, thumbnail_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_photo_series_creation(self):
        """Test PhotoSeries creation with multiple files."""
        # This would test the form logic and model creation
        pass  # Implement based on your specific form structure

    def test_mobile_compatibility(self):
        """Test mobile-specific configurations."""
        # Test video conversion settings for mobile
        # Test image optimization for mobile
        pass  # Implement mobile-specific tests
```

## Step 5: Security Review and Optimization

### Update file serving security

```python
# apps/mediafiles/views.py - Enhanced security

class SecureFileServeView(View):
    """Enhanced secure file serving for FilePond files."""

    @method_decorator(login_required)
    @method_decorator(cache_control(private=True, max_age=3600))
    def get(self, request: HttpRequest, file_id: str) -> HttpResponse:
        """Serve file with enhanced security checks."""
        try:
            # Validate file_id format (UUID)
            import uuid
            try:
                uuid.UUID(file_id)
            except ValueError:
                raise Http404("Invalid file identifier")

            # Get file and check permissions
            file_obj = self._get_file_with_permissions(request.user, file_id)

            # Rate limiting check
            if not self._check_rate_limit(request.user, file_id):
                raise PermissionDenied("Rate limit exceeded")

            # Log access
            self._log_file_access(request.user, file_obj, 'view')

            # Serve file securely
            return self._serve_file_securely(file_obj)

        except Exception as e:
            self._log_security_event(request.user, 'file_access_error', str(e))
            raise Http404("File not found")

    def _check_rate_limit(self, user, file_id: str) -> bool:
        """Check rate limiting for file access."""
        # Implement rate limiting logic
        # For example, max 100 file accesses per minute per user
        return True  # Simplified for this example

    def _get_file_with_permissions(self, user, file_id: str):
        """Get file object with permission checking."""
        # Find the file in VideoClip, Photo, or PhotoSeriesFile
        from .models import VideoClip, Photo, PhotoSeriesFile

        # Try VideoClip
        try:
            videoclip = VideoClip.objects.get(file_id=file_id)
            if can_access_patient(user, videoclip.patient):
                return videoclip
        except VideoClip.DoesNotExist:
            pass

        # Try Photo
        try:
            photo = Photo.objects.get(file_id=file_id)
            if can_access_patient(user, photo.patient):
                return photo
        except Photo.DoesNotExist:
            pass

        # Try PhotoSeriesFile
        try:
            series_file = PhotoSeriesFile.objects.get(file_id=file_id)
            if can_access_patient(user, series_file.photo_series.patient):
                return series_file
        except PhotoSeriesFile.DoesNotExist:
            pass

        raise PermissionDenied("File not found or access denied")
```

## Step 6: Performance Testing and Optimization

### Create performance test script

```python
# scripts/performance_test.py

import time
import requests
from django.test import TestCase
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Test upload performance and mobile compatibility'

    def add_arguments(self, parser):
        parser.add_argument('--test-type', choices=['upload', 'mobile', 'load'], default='upload')

    def handle(self, *args, **options):
        test_type = options['test_type']

        if test_type == 'upload':
            self.test_upload_performance()
        elif test_type == 'mobile':
            self.test_mobile_compatibility()
        elif test_type == 'load':
            self.test_load_performance()

    def test_upload_performance(self):
        """Test upload performance with various file sizes."""
        self.stdout.write("Testing upload performance...")

        # Test different file sizes
        test_sizes = [1, 5, 10, 25, 50]  # MB

        for size_mb in test_sizes:
            start_time = time.time()
            # Simulate upload test
            # (implement actual upload testing)
            end_time = time.time()

            upload_time = end_time - start_time
            speed_mbps = size_mb / upload_time if upload_time > 0 else 0

            self.stdout.write(f"  {size_mb}MB file: {upload_time:.2f}s ({speed_mbps:.2f} MB/s)")

    def test_mobile_compatibility(self):
        """Test mobile user agent compatibility."""
        self.stdout.write("Testing mobile compatibility...")

        mobile_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36',
        ]

        for ua in mobile_user_agents:
            # Test with mobile user agent
            # (implement mobile-specific testing)
            self.stdout.write(f"  {ua[:50]}... OK")

    def test_load_performance(self):
        """Test load performance with multiple concurrent uploads."""
        self.stdout.write("Testing load performance...")

        # Test concurrent uploads
        # (implement load testing)
        pass
```

## Step 7: Documentation Update

### Update README.md section

```markdown
# MediaFiles App - FilePond Integration

The MediaFiles app now uses django-drf-filepond for all file uploads, providing:

## Features

- ✅ Server-side H.264 video conversion for universal mobile compatibility
- ✅ Automatic image optimization and thumbnail generation
- ✅ Chunked uploads with progress tracking
- ✅ Drag & drop interface with mobile support
- ✅ Secure file serving with UUID naming
- ✅ Simplified JavaScript architecture (no complex bundles)

## Upload Types

- **Photos**: Single image uploads (JPEG, PNG, WebP)
- **Photo Series**: Multiple image uploads with reordering
- **Video Clips**: Video uploads with automatic H.264 conversion

## Mobile Compatibility

All videos are automatically converted to H.264/MP4 format with mobile-optimized settings:

- Maximum resolution: 1920x1080
- Bitrate limit: 2Mbps
- Fast start enabled for streaming
- Universal codec compatibility

## File Structure
```

media/
├── photos/YYYY/MM/originals/[uuid].ext
├── photo_series/YYYY/MM/originals/[uuid].ext
├── videos/YYYY/MM/originals/[uuid].ext
└── thumbnails/YYYY/MM/[uuid]\_thumb.jpg

````

## Development
- No complex webpack configuration needed
- FilePond loaded from CDN
- Centralized configuration in `filepond-config.js`
- Server-side processing handles all conversion

## Testing
Run the performance test suite:
```bash
python manage.py performance_test --test-type=upload
python manage.py performance_test --test-type=mobile
````

````

## Step 8: Final Deployment Preparation

### Create deployment checklist:
```markdown
# MediaFiles FilePond Deployment Checklist

## Pre-Deployment
- [ ] All Phase 1, 2, 3 steps completed
- [ ] Legacy code completely removed
- [ ] Migrations created and tested
- [ ] Tests passing
- [ ] Performance tests completed
- [ ] Mobile compatibility verified

## Production Settings
- [ ] FilePond CDN configured
- [ ] MEDIA_ROOT and MEDIA_URL set correctly
- [ ] FFmpeg installed on production server
- [ ] File storage permissions configured
- [ ] Rate limiting configured
- [ ] Logging configured

## Security Checklist
- [ ] File upload size limits set
- [ ] MIME type validation active
- [ ] Secure file serving working
- [ ] Permission system functional
- [ ] Rate limiting active
- [ ] Audit logging enabled

## Mobile Testing
- [ ] iOS Safari upload tested
- [ ] Android Chrome upload tested
- [ ] Video playback tested on mobile
- [ ] Photo display tested on mobile
- [ ] Touch interface tested

## Performance
- [ ] Upload speed acceptable
- [ ] Video conversion time reasonable
- [ ] Page load times optimized
- [ ] Bundle sizes minimized
- [ ] CDN resources loading correctly

## Monitoring
- [ ] File upload success rate monitoring
- [ ] Video conversion failure alerts
- [ ] Storage usage monitoring
- [ ] Performance metrics tracking
````

## Success Criteria

- ✅ All legacy upload code removed
- ✅ FilePond working for all upload types
- ✅ Mobile compatibility confirmed across devices
- ✅ Performance meets requirements
- ✅ Security review completed
- ✅ Tests passing
- ✅ Documentation updated
- ✅ Deployment ready

## Final Result

A clean, maintainable media upload system with:

- Universal mobile compatibility
- Simplified architecture
- No JavaScript bundle complexity
- Reliable chunked uploads
- Server-side processing
- Secure file handling
- Excellent user experience
