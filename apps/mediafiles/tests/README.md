# MediaFiles App Testing Infrastructure

This directory contains the comprehensive testing infrastructure for the MediaFiles app, implementing the testing framework specified in Step 9 of the implementation plan.

## Test Structure

### Test Files

- **`test_models.py`** - Model validation and behavior tests
- **`test_views.py`** - View functionality and permissions tests
- **`test_forms.py`** - Form validation and file handling tests
- **`test_utils.py`** - Utility function testing
- **`test_security.py`** - Security validation and file naming tests
- **`test_validators.py`** - File validation and sanitization tests

### Test Media Files

The `test_media/` directory contains sample files for testing:

#### Valid Test Files

- `small_image.jpg` - Small JPEG image (100x100)
- `medium_image.jpg` - Medium JPEG image (500x500)
- `large_image.jpg` - Large JPEG image (1920x1080)
- `test_image.png` - PNG image with transparency
- `test_image.webp` - WebP image (if supported)
- `duplicate_image.jpg` - Duplicate of small_image.jpg for deduplication testing
- `test_video.mp4` - Valid MP4 video file (mock)
- `test_video.webm` - Valid WebM video file (mock)
- `test_video.mov` - Valid QuickTime video file (mock)
- `large_video.mp4` - Large video file for size testing

#### Invalid/Malicious Test Files

- `fake_image.jpg` - Text file disguised as image
- `malicious.jpg` - HTML file with XSS content disguised as image
- `malicious.png` - PHP file disguised as image
- `malicious.mp4` - JavaScript file disguised as video
- `polyglot.jpg` - Binary file with embedded script content

#### Dangerous Filename Tests

The `dangerous_names/` subdirectory contains files with various filename patterns:

- Normal filenames
- Files with spaces, dashes, underscores
- Uppercase filenames
- Files with dots in names
- Files with numbers
- Files with Unicode characters and accents

## Running Tests

### Quick Test Run

```bash
# Run all mediafiles tests
uv run python manage.py test apps.mediafiles.tests

# Run specific test module
uv run python manage.py test apps.mediafiles.tests.test_models
```

### Using the Test Runner Script

```bash
# Run comprehensive test suite
cd apps/mediafiles/tests
python run_tests.py
```

The test runner script will:

- Run all test modules
- Perform Django system checks
- Check for missing migrations
- Provide a summary of results

### Individual Test Categories

```bash
# Model tests
uv run python manage.py test apps.mediafiles.tests.test_models

# View tests
uv run python manage.py test apps.mediafiles.tests.test_views

# Form tests
uv run python manage.py test apps.mediafiles.tests.test_forms

# Utility tests
uv run python manage.py test apps.mediafiles.tests.test_utils

# Security tests
uv run python manage.py test apps.mediafiles.tests.test_security

# Validator tests
uv run python manage.py test apps.mediafiles.tests.test_validators
```

## Test Configuration

### Test Settings

The `test_settings.py` file provides test-specific configuration:

- Temporary media directories
- Reduced file size limits for faster testing
- In-memory database for speed
- Simplified middleware stack
- Test-specific security settings

### Using Test Settings

```python
from apps.mediafiles.tests.test_settings import apply_test_settings
apply_test_settings(settings)
```

## Test Categories

### 1. Model Tests (`test_models.py`)

- MediaFile model creation and validation
- Photo, PhotoSeries, and VideoClip model behavior
- Event model integration
- Patient-media relationships
- User permissions on media files

### 2. View Tests (`test_views.py`)

- Media file upload views
- File serving and download views
- Permission-based access control
- Cross-user access prevention
- Anonymous user access denial

### 3. Form Tests (`test_forms.py`)

- File upload form validation
- File type and size validation
- Multiple file handling (photo series)
- Malicious file rejection
- Form integration with models

### 4. Utility Tests (`test_utils.py`)

- Secure file path generation
- Filename normalization and cleaning
- File hash calculation for deduplication
- File extension validation
- Image and video processing utilities

### 5. Security Tests (`test_security.py`)

- UUID-based filename generation
- Dangerous filename sanitization
- File content security validation
- Malicious file detection
- Path traversal prevention
- File deduplication functionality

### 6. Validator Tests (`test_validators.py`)

- Image file format validation
- Video file format validation
- File size validation
- MIME type validation
- File extension validation
- Filename sanitization
- Malicious content detection

## Security Testing

The testing infrastructure includes comprehensive security testing:

### File Naming Security

- UUID-based filename generation
- Prevention of path traversal attacks
- Sanitization of dangerous characters
- Unicode filename handling

### File Content Security

- Magic number validation
- MIME type verification
- Malicious content detection
- Polyglot file detection
- Script injection prevention

### Access Control Testing

- User permission verification
- Cross-user access prevention
- Anonymous access denial
- File serving security

## Test Data Management

### Creating Test Media Files

The `create_test_media.py` script generates all necessary test files:

```bash
cd apps/mediafiles/tests
python create_test_media.py
```

### Test Data Helpers

The `test_settings.py` provides helper functions:

```python
from apps.mediafiles.tests.test_settings import (
    get_test_image_path,
    get_test_video_path,
    get_malicious_file_path
)
```

## Implementation Status

### Phase 1 (Current)

- ✅ Test infrastructure created
- ✅ Test media files generated
- ✅ Test structure established
- ✅ Security test framework ready
- ✅ Validator test framework ready

### Phase 2 (Future)

- ⏳ Model implementation and testing
- ⏳ Form implementation and testing
- ⏳ View implementation and testing
- ⏳ Utility function implementation and testing

## Best Practices

### Writing Tests

1. Use descriptive test method names
2. Include docstrings for test methods
3. Use `setUp()` for common test data
4. Use `subTest()` for parameterized tests
5. Test both positive and negative cases
6. Include security-focused test cases

### Test Data

1. Use realistic test data
2. Include edge cases and boundary conditions
3. Test with various file sizes and types
4. Include malicious file samples
5. Test Unicode and international content

### Security Testing

1. Test all file validation functions
2. Include path traversal attempts
3. Test malicious file detection
4. Verify access control mechanisms
5. Test file serving security

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

- Fast execution with in-memory database
- Comprehensive coverage reporting
- Security vulnerability detection
- Performance regression testing

## Troubleshooting

### Common Issues

1. **Missing test media files**: Run `create_test_media.py`
2. **Permission errors**: Check file permissions in test_media/
3. **Import errors**: Ensure all dependencies are installed
4. **Database errors**: Use test settings with in-memory database

### Debug Mode

Set `DEBUG=True` in test settings for detailed error information.

### Verbose Testing

Use `-v 2` flag for verbose test output:

```bash
uv run python manage.py test apps.mediafiles.tests -v 2
```
