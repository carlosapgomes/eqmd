# MediaFiles Security Tests
# Tests for security validation and file naming

import os
import tempfile
import uuid
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.mediafiles.utils import (
    get_secure_upload_path,
    normalize_filename,
    calculate_file_hash,
    clean_filename
)

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
        
        # TODO: Implement when security module is available
        # is_secure = validate_file_security(valid_file, 'image')
        # self.assertTrue(is_secure)
        pass
    
    def test_malicious_file_detection(self):
        """Test detection of malicious files"""
        # File with script content disguised as image
        malicious_content = b"<script>alert('xss')</script>" + self.valid_image_content
        malicious_file = SimpleUploadedFile(
            "malicious.jpg",
            malicious_content,
            content_type="image/jpeg"
        )
        
        # TODO: Implement when security module is available
        # is_malicious = check_malicious_content(malicious_file)
        # self.assertTrue(is_malicious)
        pass
    
    def test_file_extension_mismatch(self):
        """Test detection of file extension mismatches"""
        # Text file with image extension
        text_file = SimpleUploadedFile(
            "fake_image.jpg",
            b"This is just text content, not an image",
            content_type="text/plain"
        )
        
        # TODO: Implement when security module is available
        # is_secure = validate_file_security(text_file, 'image')
        # self.assertFalse(is_secure)
        pass


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
    
    def test_file_permission_checking(self):
        """Test file permission checking"""
        # TODO: Implement when models are available
        pass
    
    def test_unauthorized_file_access(self):
        """Test prevention of unauthorized file access"""
        # TODO: Implement when views are available
        pass


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
