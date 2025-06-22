# MediaFiles Security Tests
# Tests for security validation and file naming

import os
import tempfile
import uuid
from django.test import TestCase, override_settings, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from apps.mediafiles.utils import (
    get_secure_upload_path,
    normalize_filename,
    calculate_file_hash,
    clean_filename
)
from apps.mediafiles.models import MediaFile, Photo
from apps.mediafiles.security import SecurityValidator, AccessController
from apps.mediafiles.validators import FileSecurityValidator, validate_media_file
from apps.mediafiles.forms import PhotoCreateForm
from apps.patients.models import Patient

User = get_user_model()


class SecureFileNamingTests(TestCase):
    """Tests for secure file naming functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_uuid_filename_generation(self):
        """Test that filenames are generated with UUIDs"""
        # Create a mock instance for testing
        class MockInstance:
            def __init__(self):
                self.id = 1
        
        instance = MockInstance()
        original_filename = "test_image.jpg"
        
        # Generate secure path
        secure_path = get_secure_upload_path(instance, original_filename)
        
        # Check that path contains UUID-like structure
        self.assertIn('/', secure_path)
        filename = os.path.basename(secure_path)
        
        # Should not contain original filename
        self.assertNotIn('test_image', filename)
        
        # Should have proper extension
        self.assertTrue(filename.endswith('.jpg'))
        
        # Should be UUID-like (36 chars + extension)
        name_without_ext = filename.rsplit('.', 1)[0]
        self.assertEqual(len(name_without_ext), 36)  # UUID length
    
    def test_filename_normalization(self):
        """Test filename normalization"""
        test_cases = [
            ("Test File.jpg", "test_file.jpg"),
            ("Arquivo com Acentos.png", "arquivo_com_acentos.png"),
            ("File with Spaces.jpeg", "file_with_spaces.jpeg"),
            ("UPPERCASE.PNG", "uppercase.png"),
            ("file-with-dashes.jpg", "file_with_dashes.jpg"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                normalized = normalize_filename(original)
                self.assertEqual(normalized, expected)
    
    def test_dangerous_filename_cleaning(self):
        """Test cleaning of dangerous filenames"""
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "file<script>alert('xss')</script>.jpg",
            "file|rm -rf /.jpg",
            "file;cat /etc/passwd.jpg",
            "file`whoami`.jpg",
            "file$(whoami).jpg",
            "file&echo test.jpg",
            "file\x00.jpg",  # null byte
            "file\n.jpg",    # newline
            "file\r.jpg",    # carriage return
        ]
        
        for dangerous_name in dangerous_filenames:
            with self.subTest(filename=dangerous_name):
                cleaned = clean_filename(dangerous_name)
                
                # Should not contain path traversal
                self.assertNotIn('..', cleaned)
                self.assertNotIn('/', cleaned)
                self.assertNotIn('\\', cleaned)
                
                # Should not contain dangerous characters
                dangerous_chars = ['<', '>', '|', ';', '`', '$', '&', '\x00', '\n', '\r']
                for char in dangerous_chars:
                    self.assertNotIn(char, cleaned)
    
    def test_file_hash_calculation(self):
        """Test file hash calculation for deduplication"""
        # Create test file content
        content1 = b"This is test content for file 1"
        content2 = b"This is test content for file 2"
        content1_duplicate = b"This is test content for file 1"
        
        file1 = SimpleUploadedFile("test1.jpg", content1, content_type="image/jpeg")
        file2 = SimpleUploadedFile("test2.jpg", content2, content_type="image/jpeg")
        file1_dup = SimpleUploadedFile("test1_dup.jpg", content1_duplicate, content_type="image/jpeg")
        
        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)
        hash1_dup = calculate_file_hash(file1_dup)
        
        # Same content should produce same hash
        self.assertEqual(hash1, hash1_dup)
        
        # Different content should produce different hash
        self.assertNotEqual(hash1, hash2)
        
        # Hash should be SHA-256 (64 hex characters)
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))


class FileSecurityValidationTests(TestCase):
    """Tests for file security validation"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )
    
    def test_valid_image_file_security(self):
        """Test security validation of valid image files"""
        valid_file = SimpleUploadedFile(
            "test.jpg",
            self.valid_image_content,
            content_type="image/jpeg"
        )

        # Test that valid files pass security validation
        try:
            metadata = validate_media_file(valid_file, 'image')
            self.assertIn('mime_type', metadata)
            self.assertEqual(metadata['mime_type'], 'image/jpeg')
        except ValidationError:
            self.fail("Valid image file should pass security validation")

    def test_malicious_file_detection(self):
        """Test detection of malicious files"""
        # File with script content disguised as image
        malicious_content = b"<script>alert('xss')</script>" + self.valid_image_content
        malicious_file = SimpleUploadedFile(
            "malicious.jpg",
            malicious_content,
            content_type="image/jpeg"
        )

        # Test that malicious content is detected
        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_content(malicious_file)

    def test_file_extension_mismatch(self):
        """Test detection of file extension mismatches"""
        # Text file with image extension
        text_file = SimpleUploadedFile(
            "fake_image.jpg",
            b"This is just text content, not an image",
            content_type="text/plain"
        )

        # Test that extension mismatch is detected
        with self.assertRaises(ValidationError):
            validate_media_file(text_file, 'image')

    def test_executable_file_detection(self):
        """Test detection of executable files disguised as images"""
        # PE executable header disguised as image
        pe_header = b'\x4d\x5a\x90\x00'  # PE executable signature
        fake_image = SimpleUploadedFile(
            "malware.jpg",
            pe_header + b"fake image content",
            content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_content(fake_image)

    def test_path_traversal_in_filename(self):
        """Test detection of path traversal attempts in filenames"""
        dangerous_filenames = [
            "../../../etc/passwd.jpg",
            "..\\..\\windows\\system32\\config.jpg",
            "file/../../secret.jpg",
            "file\\..\\..\\secret.jpg"
        ]

        for dangerous_name in dangerous_filenames:
            with self.subTest(filename=dangerous_name):
                with self.assertRaises(ValidationError):
                    FileSecurityValidator.validate_filename_security(dangerous_name)

    def test_null_byte_injection(self):
        """Test detection of null byte injection in filenames"""
        null_byte_filename = "image.jpg\x00.exe"

        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_filename_security(null_byte_filename)

    def test_oversized_file_rejection(self):
        """Test rejection of oversized files"""
        # Create a large file content
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB (over 5MB limit)
        large_file = SimpleUploadedFile(
            "large.jpg",
            large_content,
            content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_size(large_file, 'image')


class FileAccessControlTests(TestCase):
    """Tests for file access control and permissions"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        # Create test patient
        self.patient = Patient.objects.create(
            name="Test Patient",
            birth_date="1990-01-01",
            created_by=self.user1,
            updated_by=self.user1
        )

        # Create test media file and photo
        self.test_image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )

        uploaded_file = SimpleUploadedFile(
            "test.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )

        self.media_file = MediaFile.objects.create_from_upload(uploaded_file)
        self.photo = Photo.objects.create(
            media_file=self.media_file,
            description="Test photo",
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user1,
            updated_by=self.user1
        )

    def test_file_permission_checking(self):
        """Test file permission checking"""
        # Test that creator can access their photo
        self.assertTrue(AccessController.check_patient_permissions(self.user1, self.patient))

        # Test hospital context checking
        self.assertTrue(AccessController.check_hospital_context(self.user1, self.patient))

    def test_unauthorized_file_access(self):
        """Test prevention of unauthorized file access"""
        # Test that user2 cannot access user1's photo without proper permissions
        self.client.force_login(self.user2)

        # Try to access photo detail view
        response = self.client.get(reverse('mediafiles:photo_detail', kwargs={'pk': self.photo.pk}))

        # Should be denied access (403 or redirect to login)
        self.assertIn(response.status_code, [403, 302])

    def test_file_enumeration_prevention(self):
        """Test prevention of file enumeration attacks"""
        # Test that direct file access by UUID is protected
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})

        # Unauthenticated access should be denied
        response = self.client.get(file_url)
        self.assertIn(response.status_code, [401, 302, 403])

        # Authenticated but unauthorized access should be denied
        self.client.force_login(self.user2)
        response = self.client.get(file_url)
        self.assertIn(response.status_code, [403, 404])

    def test_secure_file_serving(self):
        """Test secure file serving with proper headers"""
        self.client.force_login(self.user1)

        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})
        response = self.client.get(file_url)

        if response.status_code == 200:
            # Check security headers
            self.assertIn('Content-Type', response)
            self.assertEqual(response['Content-Type'], 'image/jpeg')

            # Check that filename is not exposed in headers
            content_disposition = response.get('Content-Disposition', '')
            self.assertNotIn(str(self.media_file.id), content_disposition)

    def test_thumbnail_access_control(self):
        """Test access control for thumbnail serving"""
        thumbnail_url = reverse('mediafiles:serve_thumbnail', kwargs={'file_id': self.media_file.id})

        # Unauthenticated access should be denied
        response = self.client.get(thumbnail_url)
        self.assertIn(response.status_code, [401, 302, 403])

        # Authorized access should work
        self.client.force_login(self.user1)
        response = self.client.get(thumbnail_url)
        # Should either serve thumbnail or return 404 if not generated yet
        self.assertIn(response.status_code, [200, 404])


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class FileDeduplicationTests(TestCase):
    """Tests for file deduplication functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.test_content = b"This is test content for deduplication testing"
    
    def test_duplicate_file_detection(self):
        """Test detection of duplicate files"""
        file1 = SimpleUploadedFile("file1.jpg", self.test_content, content_type="image/jpeg")
        file2 = SimpleUploadedFile("file2.jpg", self.test_content, content_type="image/jpeg")
        
        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)
        
        # Same content should produce same hash
        self.assertEqual(hash1, hash2)
    
    def test_unique_file_handling(self):
        """Test handling of unique files"""
        content1 = b"This is unique content 1"
        content2 = b"This is unique content 2"
        
        file1 = SimpleUploadedFile("file1.jpg", content1, content_type="image/jpeg")
        file2 = SimpleUploadedFile("file2.jpg", content2, content_type="image/jpeg")
        
        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)
        
        # Different content should produce different hashes
        self.assertNotEqual(hash1, hash2)


class MIMETypeSpoofingTests(TestCase):
    """Tests for MIME type spoofing detection"""

    def test_javascript_disguised_as_image(self):
        """Test detection of JavaScript files disguised as images"""
        js_content = b"alert('XSS attack');"
        fake_image = SimpleUploadedFile(
            "script.jpg",
            js_content,
            content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            validate_media_file(fake_image, 'image')

    def test_html_disguised_as_image(self):
        """Test detection of HTML files disguised as images"""
        html_content = b"<html><script>alert('XSS')</script></html>"
        fake_image = SimpleUploadedFile(
            "page.jpg",
            html_content,
            content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_content(fake_image)

    def test_php_disguised_as_image(self):
        """Test detection of PHP files disguised as images"""
        php_content = b"<?php system($_GET['cmd']); ?>"
        fake_image = SimpleUploadedFile(
            "shell.jpg",
            php_content,
            content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_content(fake_image)

    def test_svg_with_javascript(self):
        """Test detection of SVG files with embedded JavaScript"""
        svg_content = b'''<svg xmlns="http://www.w3.org/2000/svg">
            <script>alert('XSS')</script>
        </svg>'''

        malicious_svg = SimpleUploadedFile(
            "image.svg",
            svg_content,
            content_type="image/svg+xml"
        )

        # SVG should be rejected as it's not in allowed image types
        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_extension("image.svg", 'image')

        # Also test content validation
        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_content(malicious_svg)


class FormSecurityTests(TestCase):
    """Tests for form-level security validation"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.patient = Patient.objects.create(
            name="Test Patient",
            birth_date="1990-01-01",
            created_by=self.user,
            updated_by=self.user
        )

        self.valid_image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda'
            b'\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )

    def test_form_malicious_file_rejection(self):
        """Test that forms reject malicious files"""
        malicious_content = b"<script>alert('xss')</script>"
        malicious_file = SimpleUploadedFile(
            "malicious.jpg",
            malicious_content,
            content_type="image/jpeg"
        )

        form_data = {
            'description': 'Test photo',
            'event_datetime': timezone.now(),
            'caption': 'Test caption'
        }

        form = PhotoCreateForm(
            data=form_data,
            files={'image': malicious_file},
            patient=self.patient,
            user=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_form_oversized_file_rejection(self):
        """Test that forms reject oversized files"""
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        large_file = SimpleUploadedFile(
            "large.jpg",
            large_content,
            content_type="image/jpeg"
        )

        form_data = {
            'description': 'Test photo',
            'event_datetime': timezone.now(),
            'caption': 'Test caption'
        }

        form = PhotoCreateForm(
            data=form_data,
            files={'image': large_file},
            patient=self.patient,
            user=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_form_invalid_extension_rejection(self):
        """Test that forms reject files with invalid extensions"""
        text_file = SimpleUploadedFile(
            "document.txt",
            b"This is a text file",
            content_type="text/plain"
        )

        form_data = {
            'description': 'Test photo',
            'event_datetime': timezone.now(),
            'caption': 'Test caption'
        }

        form = PhotoCreateForm(
            data=form_data,
            files={'image': text_file},
            patient=self.patient,
            user=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)


class SecuritySettingsTests(TestCase):
    """Tests for security settings validation"""

    def test_uuid_filename_setting(self):
        """Test that UUID filename setting is properly configured"""
        # This should be True for security
        uuid_enabled = getattr(settings, 'MEDIA_USE_UUID_FILENAMES', False)
        self.assertTrue(uuid_enabled, "UUID filenames should be enabled for security")

    def test_file_size_limits(self):
        """Test that reasonable file size limits are configured"""
        image_max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 0)
        self.assertGreater(image_max_size, 0, "Image max size should be configured")
        self.assertLessEqual(image_max_size, 10 * 1024 * 1024, "Image max size should not exceed 10MB")

    def test_allowed_file_types(self):
        """Test that only safe file types are allowed"""
        allowed_image_types = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', [])
        self.assertIsInstance(allowed_image_types, list)
        self.assertGreater(len(allowed_image_types), 0, "At least one image type should be allowed")

        # Check that dangerous types are not allowed
        dangerous_types = ['application/x-executable', 'application/x-msdownload', 'text/html']
        for dangerous_type in dangerous_types:
            self.assertNotIn(dangerous_type, allowed_image_types)

    def test_allowed_extensions(self):
        """Test that only safe extensions are allowed"""
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', [])
        self.assertIsInstance(allowed_extensions, list)
        self.assertGreater(len(allowed_extensions), 0, "At least one extension should be allowed")

        # Check that dangerous extensions are not allowed
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.php', '.asp', '.jsp']
        for dangerous_ext in dangerous_extensions:
            self.assertNotIn(dangerous_ext, allowed_extensions)


class FileSystemSecurityTests(TestCase):
    """Tests for file system security"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_secure_path_generation(self):
        """Test that secure paths are generated correctly"""
        class MockInstance:
            def __init__(self):
                self.id = 1

        instance = MockInstance()
        filename = "test_image.jpg"

        secure_path = get_secure_upload_path(instance, filename)

        # Path should not contain original filename
        self.assertNotIn('test_image', secure_path)

        # Path should contain year/month structure
        self.assertRegex(secure_path, r'\d{4}/\d{2}/')

        # Path should end with .jpg
        self.assertTrue(secure_path.endswith('.jpg'))

        # Path should not contain dangerous patterns
        self.assertNotIn('..', secure_path)
        self.assertNotIn('//', secure_path)

    def test_filename_sanitization(self):
        """Test filename sanitization"""
        dangerous_filename = "../../../etc/passwd<script>alert('xss')</script>.jpg"
        cleaned = clean_filename(dangerous_filename)

        # Should not contain dangerous characters
        self.assertNotIn('..', cleaned)
        self.assertNotIn('<', cleaned)
        self.assertNotIn('>', cleaned)
        self.assertNotIn('script', cleaned)

        # Should still have extension
        self.assertTrue(cleaned.endswith('.jpg'))

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/etc/passwd",
            "C:\\windows\\system32\\config"
        ]

        for dangerous_path in dangerous_paths:
            with self.subTest(path=dangerous_path):
                self.assertFalse(SecurityValidator.validate_file_path_security(dangerous_path))

    def test_file_hash_consistency(self):
        """Test that file hashes are consistent and secure"""
        content = b"Test file content for hashing"
        file1 = SimpleUploadedFile("test1.jpg", content, content_type="image/jpeg")
        file2 = SimpleUploadedFile("test2.jpg", content, content_type="image/jpeg")

        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)

        # Same content should produce same hash
        self.assertEqual(hash1, hash2)

        # Hash should be SHA-256 (64 hex characters)
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))

        # Hash should be deterministic
        hash3 = calculate_file_hash(file1)
        self.assertEqual(hash1, hash3)
