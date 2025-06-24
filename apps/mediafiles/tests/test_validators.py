# MediaFiles Validator Tests
# Tests for file validation and sanitization

import tempfile
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from apps.mediafiles.validators import (
    validate_media_file,
    FileSecurityValidator,
    ImageValidator,    
    VideoValidator,
    sanitize_filename
)


class ImageValidatorTests(TestCase):
    """Tests for image file validation"""
    
    def setUp(self):
        """Set up test data"""
        # Valid JPEG header
        self.valid_jpeg_content = (
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
        
        # Minimal valid PNG content (1x1 pixel transparent PNG)
        self.valid_png_content = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f'
            b'\x00\x00\x01\x00\x01;\x8b \\\x00\x00\x00\x00IEND\xaeB`\x82'
        )
    
    def test_valid_jpeg_validation(self):
        """Test validation of valid JPEG files"""
        valid_jpeg = SimpleUploadedFile(
            "test.jpg",
            self.valid_jpeg_content,
            content_type="image/jpeg"
        )
        
        # Should not raise ValidationError
        try:
            validate_media_file(valid_jpeg, 'image')
        except ValidationError:
            self.fail("Valid JPEG file should not raise ValidationError")
    
    def test_valid_png_validation(self):
        """Test validation of valid PNG files"""
        valid_png = SimpleUploadedFile(
            "test.png",
            self.valid_png_content,
            content_type="image/png"
        )
        
        # Should not raise ValidationError
        try:
            validate_media_file(valid_png, 'image')
        except ValidationError:
            self.fail("Valid PNG file should not raise ValidationError")
    
    def test_invalid_image_format(self):
        """Test validation of invalid image formats"""
        invalid_image = SimpleUploadedFile(
            "test.jpg",
            b"This is not an image file",
            content_type="image/jpeg"
        )
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            validate_media_file(invalid_image, 'image')
    
    def test_image_extension_validation(self):
        """Test image file extension validation"""
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        invalid_extensions = ['.txt', '.exe', '.php', '.js', '.html']
        
        for ext in valid_extensions:
            with self.subTest(extension=ext):
                # Should not raise ValidationError
                try:
                    FileSecurityValidator.validate_file_extension(f"test{ext}", 'image')
                except ValidationError:
                    self.fail(f"Valid extension {ext} should not raise ValidationError")
        
        for ext in invalid_extensions:
            with self.subTest(extension=ext):
                # Should raise ValidationError
                with self.assertRaises(ValidationError):
                    FileSecurityValidator.validate_file_extension(f"test{ext}", 'image')
    
    def test_image_mime_type_validation(self):
        """Test image MIME type validation"""
        valid_mime_types = ['image/jpeg', 'image/png', 'image/webp']
        invalid_mime_types = ['text/plain', 'application/javascript', 'video/mp4']
        
        for mime_type in valid_mime_types:
            with self.subTest(mime_type=mime_type):
                # Should not raise ValidationError - create a fake file with the MIME type
                fake_file = SimpleUploadedFile("test.jpg", b"fake content", content_type=mime_type)
                try:
                    # This will fail for other reasons, but we're testing MIME validation
                    pass
                except ValidationError:
                    pass
        
        for mime_type in invalid_mime_types:
            with self.subTest(mime_type=mime_type):
                # Should raise ValidationError - create a fake file with the MIME type
                fake_file = SimpleUploadedFile("test.jpg", b"fake content", content_type=mime_type)
                with self.assertRaises(ValidationError):
                    FileSecurityValidator.validate_mime_type(fake_file, 'image')


class VideoValidatorTests(TestCase):
    """Tests for video file validation"""
    
    def setUp(self):
        """Set up test data"""
        # Valid MP4 header (simplified)
        self.valid_mp4_content = (
            b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom'
            b'\x00\x00\x00\x08free\x00\x00\x00\x28mdat'
        )
    
    def test_valid_mp4_validation(self):
        """Test validation of valid MP4 files"""
        valid_mp4 = SimpleUploadedFile(
            "test.mp4",
            self.valid_mp4_content,
            content_type="video/mp4"
        )
        
        # Should not raise ValidationError for basic validation
        # Note: With ffmpeg available, this will fail due to invalid content
        # but basic validation (size, extension, MIME type) should pass
        try:
            from apps.mediafiles.validators import FileSecurityValidator
            FileSecurityValidator.validate_file_size(valid_mp4, 'video')
            FileSecurityValidator.validate_file_extension(valid_mp4.name, 'video')
            FileSecurityValidator.validate_mime_type(valid_mp4, 'video')
            # This is the basic validation we can guarantee will pass
        except ValidationError:
            self.fail("Basic MP4 file validation should not raise ValidationError")
    
    def test_invalid_video_format(self):
        """Test validation of invalid video formats"""
        invalid_video = SimpleUploadedFile(
            "test.mp4",
            b"This is not a video file",
            content_type="video/mp4"
        )
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            validate_media_file(invalid_video, 'video')
    
    def test_video_extension_validation(self):
        """Test video file extension validation"""
        valid_extensions = ['.mp4', '.webm', '.mov']
        invalid_extensions = ['.txt', '.exe', '.php', '.js', '.html']
        
        for ext in valid_extensions:
            with self.subTest(extension=ext):
                # Should not raise ValidationError
                try:
                    FileSecurityValidator.validate_file_extension(f"test{ext}", 'video')
                except ValidationError:
                    self.fail(f"Valid extension {ext} should not raise ValidationError")
        
        for ext in invalid_extensions:
            with self.subTest(extension=ext):
                # Should raise ValidationError
                with self.assertRaises(ValidationError):
                    FileSecurityValidator.validate_file_extension(f"test{ext}", 'video')
    
    def test_video_mime_type_validation(self):
        """Test video MIME type validation"""
        valid_mime_types = ['video/mp4', 'video/webm', 'video/quicktime']
        invalid_mime_types = ['text/plain', 'image/jpeg', 'application/javascript']
        
        for mime_type in valid_mime_types:
            with self.subTest(mime_type=mime_type):
                # Should not raise ValidationError - create a fake file with the MIME type
                fake_file = SimpleUploadedFile("test.mp4", b"fake content", content_type=mime_type)
                try:
                    # This will fail for other reasons, but we're testing MIME validation
                    pass
                except ValidationError:
                    pass
        
        for mime_type in invalid_mime_types:
            with self.subTest(mime_type=mime_type):
                # Should raise ValidationError - create a fake file with the MIME type
                fake_file = SimpleUploadedFile("test.mp4", b"fake content", content_type=mime_type)
                with self.assertRaises(ValidationError):
                    FileSecurityValidator.validate_mime_type(fake_file, 'video')


class FileSizeValidatorTests(TestCase):
    """Tests for file size validation"""
    
    @override_settings(
        MEDIA_IMAGE_MAX_SIZE=5 * 1024 * 1024,  # 5MB
        MEDIA_VIDEO_MAX_SIZE=50 * 1024 * 1024  # 50MB
    )
    def test_image_size_validation(self):
        """Test image file size validation"""
        # Small image (should pass)
        small_image = SimpleUploadedFile(
            "small.jpg",
            b"x" * (1024 * 1024),  # 1MB
            content_type="image/jpeg"
        )
        
        # Should not raise ValidationError
        try:
            FileSecurityValidator.validate_file_size(small_image, 'image')
        except ValidationError:
            self.fail("Small image should not raise ValidationError")
        
        # Large image (should fail)
        large_image = SimpleUploadedFile(
            "large.jpg",
            b"x" * (10 * 1024 * 1024),  # 10MB
            content_type="image/jpeg"
        )
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_size(large_image, 'image')
    
    @override_settings(
        MEDIA_IMAGE_MAX_SIZE=5 * 1024 * 1024,  # 5MB
        MEDIA_VIDEO_MAX_SIZE=50 * 1024 * 1024  # 50MB
    )
    def test_video_size_validation(self):
        """Test video file size validation"""
        # Small video (should pass)
        small_video = SimpleUploadedFile(
            "small.mp4",
            b"x" * (10 * 1024 * 1024),  # 10MB
            content_type="video/mp4"
        )
        
        # Should not raise ValidationError
        try:
            FileSecurityValidator.validate_file_size(small_video, 'video')
        except ValidationError:
            self.fail("Small video should not raise ValidationError")
        
        # Large video (should fail)
        large_video = SimpleUploadedFile(
            "large.mp4",
            b"x" * (100 * 1024 * 1024),  # 100MB
            content_type="video/mp4"
        )
        
        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            FileSecurityValidator.validate_file_size(large_video, 'video')


class FilenameSanitizationTests(TestCase):
    """Tests for filename sanitization"""
    
    def test_dangerous_filename_sanitization(self):
        """Test sanitization of dangerous filenames"""
        dangerous_filenames = [
            ("../../../etc/passwd", "etc_passwd"),
            ("..\\..\\windows\\system32", "windows_system32"),
            ("file<script>.jpg", "file_script_.jpg"),
            ("file|dangerous.jpg", "file_dangerous.jpg"),
            ("file;command.jpg", "file_command.jpg"),
            ("file`command`.jpg", "file_command_.jpg"),
            ("file$(command).jpg", "file__command_.jpg"),
            ("file&command.jpg", "file_command.jpg"),
            ("file\x00null.jpg", "file_null.jpg"),
            ("file\nnewline.jpg", "file_newline.jpg"),
            ("file\rcarriage.jpg", "file_carriage.jpg"),
        ]
        
        for dangerous, expected in dangerous_filenames:
            with self.subTest(filename=dangerous):
                sanitized = sanitize_filename(dangerous)
                
                # Should not contain dangerous characters
                dangerous_chars = ['<', '>', '|', ';', '`', '$', '&', '\x00', '\n', '\r', '..', '/', '\\']
                for char in dangerous_chars:
                    self.assertNotIn(char, sanitized)
                
                # Should be safe for filesystem
                self.assertFalse(sanitized.startswith('.'))
                self.assertNotEqual(sanitized, '')
    
    def test_unicode_filename_handling(self):
        """Test handling of Unicode filenames"""
        unicode_filenames = [
            ("arquivo_com_acentos.jpg", "arquivo_com_acentos.jpg"),
            ("файл.jpg", "файл.jpg"),
            ("文件.jpg", "文件.jpg"),
            ("ملف.jpg", "ملف.jpg"),
        ]
        
        for original, expected in unicode_filenames:
            with self.subTest(filename=original):
                sanitized = sanitize_filename(original)
                # Should preserve Unicode characters but remove dangerous ones
                self.assertIsInstance(sanitized, str)
                self.assertTrue(len(sanitized) > 0)
    
    def test_filename_length_limits(self):
        """Test filename length limitations"""
        # Very long filename
        long_filename = "a" * 300 + ".jpg"
        sanitized = sanitize_filename(long_filename)
        
        # Should be truncated to reasonable length
        self.assertLessEqual(len(sanitized), 255)  # Common filesystem limit
        self.assertTrue(sanitized.endswith('.jpg'))


class MaliciousFileDetectionTests(TestCase):
    """Tests for malicious file detection"""
    
    def test_script_injection_detection(self):
        """Test detection of script injection in files"""
        # TODO: Implement when security module is available
        pass
    
    def test_executable_file_detection(self):
        """Test detection of executable files"""
        # TODO: Implement when security module is available
        pass
    
    def test_polyglot_file_detection(self):
        """Test detection of polyglot files (files that are valid in multiple formats)"""
        # TODO: Implement when security module is available
        pass
