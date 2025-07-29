# MediaFiles Form Tests
# Tests for media file forms

import os
from datetime import datetime
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.forms import ValidationError

# Note: Hospital model removed after single-hospital refactor
from apps.patients.models import Patient
from apps.mediafiles.forms import PhotoCreateForm, PhotoUpdateForm
from apps.mediafiles.models import Photo, MediaFile
from apps.events.models import Event

User = get_user_model()


class PhotoUploadFormTests(TestCase):
    """Tests for photo upload form"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

        # Load test media files
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')

        with open(os.path.join(self.test_media_dir, 'small_image.jpg'), 'rb') as f:
            self.valid_image_content = f.read()

        with open(os.path.join(self.test_media_dir, 'fake_image.jpg'), 'rb') as f:
            self.invalid_image_content = f.read()

    def create_test_image(self, filename='test.jpg'):
        """Helper method to create a test image file"""
        return SimpleUploadedFile(
            filename,
            self.valid_image_content,
            content_type='image/jpeg'
        )

    def test_photo_create_form_datetime_formatting(self):
        """Test PhotoCreateForm datetime field formatting and validation"""
        # Test with HTML5 datetime-local format (using past date)
        test_image = self.create_test_image()
        # Use a clearly past date to avoid any timezone issues
        past_datetime = timezone.now() - timezone.timedelta(days=1)
        datetime_str = past_datetime.strftime('%Y-%m-%dT%H:%M')

        form_data = {
            'description': 'Test photo description',
            'event_datetime': datetime_str,  # HTML5 format
            'caption': 'Test caption'
        }
        form = PhotoCreateForm(
            data=form_data,
            files={'image': test_image},
            patient=self.patient,
            user=self.user
        )

        # Debug: print the datetime values for troubleshooting
        if not form.is_valid():
            print(f"Current time: {timezone.now()}")
            print(f"Form datetime string: {datetime_str}")
            print(f"Parsed datetime: {form.cleaned_data.get('event_datetime') if form.cleaned_data else 'Not parsed'}")

        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_photo_create_form_datetime_with_seconds(self):
        """Test PhotoCreateForm with datetime including seconds"""
        test_image = self.create_test_image()
        past_datetime = timezone.now() - timezone.timedelta(days=1)
        form_data = {
            'description': 'Test photo description',
            'event_datetime': past_datetime.strftime('%Y-%m-%dT%H:%M:%S'),  # HTML5 format with seconds
            'caption': 'Test caption'
        }
        form = PhotoCreateForm(
            data=form_data,
            files={'image': test_image},
            patient=self.patient,
            user=self.user
        )
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_photo_create_form_datetime_brazilian_format(self):
        """Test PhotoCreateForm with Brazilian datetime format"""
        test_image = self.create_test_image()
        past_datetime = timezone.now() - timezone.timedelta(days=1)  # Use a full day in the past
        form_data = {
            'description': 'Test photo description',
            'event_datetime': past_datetime.strftime('%d/%m/%Y %H:%M:%S'),  # Brazilian format
            'caption': 'Test caption'
        }
        form = PhotoCreateForm(
            data=form_data,
            files={'image': test_image},
            patient=self.patient,
            user=self.user
        )
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_photo_create_form_datetime_initial_value_format(self):
        """Test PhotoCreateForm initial datetime value is properly formatted"""
        form = PhotoCreateForm(patient=self.patient, user=self.user)
        initial_value = form.fields['event_datetime'].initial

        # Should be in HTML5 datetime-local format (YYYY-MM-DDTHH:MM)
        self.assertIsNotNone(initial_value)
        self.assertRegex(initial_value, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$')

    def test_photo_create_form_future_datetime_validation(self):
        """Test PhotoCreateForm rejects future datetime"""
        test_image = self.create_test_image()
        future_datetime = timezone.now() + timezone.timedelta(days=1)
        form_data = {
            'description': 'Test photo description',
            'event_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Test caption'
        }
        form = PhotoCreateForm(
            data=form_data,
            files={'image': test_image},
            patient=self.patient,
            user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)


class PhotoUpdateFormTests(TestCase):
    """Tests for PhotoUpdateForm datetime formatting"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

        # Create a test photo for updating
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(self.test_media_dir, 'small_image.jpg'), 'rb') as f:
            image_content = f.read()

        test_image = SimpleUploadedFile(
            "test_image.jpg",
            image_content,
            content_type="image/jpeg"
        )
        media_file = MediaFile.objects.create_from_upload(test_image)

        self.photo = Photo.objects.create(
            media_file=media_file,
            description='Original description',
            caption='Original caption',
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            event_type=Event.PHOTO_EVENT
        )

    def test_photo_update_form_datetime_initial_value(self):
        """Test PhotoUpdateForm initial datetime value is properly formatted"""
        form = PhotoUpdateForm(instance=self.photo, user=self.user)
        initial_value = form.fields['event_datetime'].initial

        # Should be in HTML5 datetime-local format (YYYY-MM-DDTHH:MM)
        self.assertIsNotNone(initial_value)
        self.assertRegex(initial_value, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$')

    def test_photo_update_form_datetime_formatting(self):
        """Test PhotoUpdateForm datetime field formatting and validation"""
        past_datetime = timezone.now() - timezone.timedelta(days=1)
        form_data = {
            'description': 'Updated description',
            'event_datetime': past_datetime.strftime('%Y-%m-%dT%H:%M'),  # HTML5 format
            'caption': 'Updated caption'
        }
        form = PhotoUpdateForm(
            data=form_data,
            instance=self.photo,
            user=self.user
        )
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_photo_update_form_datetime_brazilian_format(self):
        """Test PhotoUpdateForm with Brazilian datetime format"""
        past_datetime = timezone.now() - timezone.timedelta(days=1)
        form_data = {
            'description': 'Updated description',
            'event_datetime': past_datetime.strftime('%d/%m/%Y %H:%M:%S'),  # Brazilian format
            'caption': 'Updated caption'
        }
        form = PhotoUpdateForm(
            data=form_data,
            instance=self.photo,
            user=self.user
        )
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_photo_update_form_future_datetime_validation(self):
        """Test PhotoUpdateForm rejects future datetime"""
        future_datetime = timezone.now() + timezone.timedelta(days=1)
        form_data = {
            'description': 'Updated description',
            'event_datetime': future_datetime.strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Updated caption'
        }
        form = PhotoUpdateForm(
            data=form_data,
            instance=self.photo,
            user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn('event_datetime', form.errors)


class PhotoSeriesUploadFormTests(TestCase):
    """Tests for photo series upload form"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

        # Load test media files
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')

        with open(os.path.join(self.test_media_dir, 'small_image.jpg'), 'rb') as f:
            self.image1_content = f.read()

        with open(os.path.join(self.test_media_dir, 'medium_image.jpg'), 'rb') as f:
            self.image2_content = f.read()

    def test_valid_photo_series_upload(self):
        """Test valid photo series upload"""
        # TODO: Implement when forms are available
        # This test will be implemented in Phase 2
        pass

    def test_photo_series_multiple_files(self):
        """Test photo series with multiple files"""
        # TODO: Implement when forms are available
        pass

    def test_photo_series_file_ordering(self):
        """Test photo series file ordering"""
        # TODO: Implement when forms are available
        pass

    def test_photo_series_minimum_files(self):
        """Test photo series minimum file requirement"""
        # TODO: Implement when forms are available
        pass


class VideoUploadFormTests(TestCase):
    """Tests for video upload form"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

        # Load test media files
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')

        with open(os.path.join(self.test_media_dir, 'test_video.mp4'), 'rb') as f:
            self.valid_video_content = f.read()

        with open(os.path.join(self.test_media_dir, 'malicious.mp4'), 'rb') as f:
            self.invalid_video_content = f.read()

    def test_valid_video_upload(self):
        """Test valid video upload"""
        # TODO: Implement when forms are available
        # This test will be implemented in Phase 2
        pass

    def test_invalid_video_upload(self):
        """Test invalid video upload"""
        # TODO: Implement when forms are available
        pass

    def test_video_file_size_validation(self):
        """Test video file size validation"""
        # TODO: Implement when forms are available
        pass

    def test_video_duration_validation(self):
        """Test video duration validation (max 2 minutes)"""
        # TODO: Implement when forms are available
        pass

    def test_video_file_type_validation(self):
        """Test video file type validation"""
        # TODO: Implement when forms are available
        pass


class DateTimeFormattingTests(TestCase):
    """Comprehensive tests for datetime formatting in mediafiles forms"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

        # Load test image
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(self.test_media_dir, 'small_image.jpg'), 'rb') as f:
            self.valid_image_content = f.read()

    def create_test_image(self, filename='test.jpg'):
        """Helper method to create a test image file"""
        return SimpleUploadedFile(
            filename,
            self.valid_image_content,
            content_type='image/jpeg'
        )

    def test_datetime_input_formats_acceptance(self):
        """Test that all configured input formats are accepted"""
        # Use past datetime to avoid future date validation error
        past_datetime = timezone.now() - timezone.timedelta(days=1)

        test_formats = [
            (past_datetime.strftime('%Y-%m-%dT%H:%M'), 'HTML5 datetime-local format'),
            (past_datetime.strftime('%Y-%m-%dT%H:%M:%S'), 'HTML5 datetime-local with seconds'),
            (past_datetime.strftime('%d/%m/%Y %H:%M:%S'), 'Brazilian format with seconds'),
            (past_datetime.strftime('%d/%m/%Y %H:%M'), 'Brazilian format without seconds'),
        ]

        for datetime_str, description in test_formats:
            with self.subTest(format=description, datetime_str=datetime_str):
                test_image = self.create_test_image()
                form_data = {
                    'description': f'Test photo - {description}',
                    'event_datetime': datetime_str,
                    'caption': 'Test caption'
                }
                form = PhotoCreateForm(
                    data=form_data,
                    files={'image': test_image},
                    patient=self.patient,
                    user=self.user
                )
                self.assertTrue(
                    form.is_valid(),
                    f"Form should accept {description} ({datetime_str}). Errors: {form.errors}"
                )

    def test_datetime_widget_format_attribute(self):
        """Test that datetime widget has correct format attribute"""
        form = PhotoCreateForm(patient=self.patient, user=self.user)
        widget = form.fields['event_datetime'].widget
        self.assertEqual(widget.format, '%Y-%m-%dT%H:%M')

    def test_datetime_widget_html5_type(self):
        """Test that datetime widget has correct HTML5 type"""
        form = PhotoCreateForm(patient=self.patient, user=self.user)
        widget = form.fields['event_datetime'].widget
        # The type is set in the widget definition in the form's Meta class
        self.assertEqual(widget.input_type, 'datetime-local')

    def test_datetime_input_formats_configuration(self):
        """Test that input_formats are properly configured"""
        form = PhotoCreateForm(patient=self.patient, user=self.user)
        expected_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',
        ]
        self.assertEqual(form.fields['event_datetime'].input_formats, expected_formats)

    def test_datetime_timezone_handling(self):
        """Test proper timezone handling in datetime formatting"""
        # Create form and check initial value is timezone-aware
        form = PhotoCreateForm(patient=self.patient, user=self.user)
        initial_value = form.fields['event_datetime'].initial

        # Parse the initial value back to datetime
        parsed_datetime = datetime.strptime(initial_value, '%Y-%m-%dT%H:%M')

        # Should be close to current time (within 1 minute)
        now = timezone.now()
        time_diff = abs((now - timezone.make_aware(parsed_datetime)).total_seconds())
        self.assertLess(time_diff, 60, "Initial datetime should be close to current time")

    def test_invalid_datetime_formats_rejection(self):
        """Test that invalid datetime formats are properly rejected"""
        # Use past dates to avoid future date validation interfering
        past_date = (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d')

        invalid_formats = [
            f'{past_date.replace("-", "/")} 14:30',  # Wrong date separator
            f'{past_date.split("-")[2]}-{past_date.split("-")[1]}-{past_date.split("-")[0]} 14:30',  # Wrong date format
            f'14:30 {past_date}',  # Time before date
            'invalid-datetime',  # Completely invalid
            '32/13/2023 25:70',  # Invalid date and time values
            '',  # Empty string
        ]

        for invalid_datetime in invalid_formats:
            with self.subTest(invalid_datetime=invalid_datetime):
                test_image = self.create_test_image()
                form_data = {
                    'description': 'Test photo',
                    'event_datetime': invalid_datetime,
                    'caption': 'Test caption'
                }
                form = PhotoCreateForm(
                    data=form_data,
                    files={'image': test_image},
                    patient=self.patient,
                    user=self.user
                )
                self.assertFalse(
                    form.is_valid(),
                    f"Form should reject invalid datetime format: {invalid_datetime}"
                )
                if invalid_datetime:  # Empty string will have different error
                    self.assertIn('event_datetime', form.errors)


class OriginalIssueRegressionTests(TestCase):
    """Regression tests for the original datetime format issue"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

        # Load test image
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(self.test_media_dir, 'small_image.jpg'), 'rb') as f:
            self.valid_image_content = f.read()

    def create_test_image(self, filename='test.jpg'):
        """Helper method to create a test image file"""
        return SimpleUploadedFile(
            filename,
            self.valid_image_content,
            content_type='image/jpeg'
        )

    def test_original_error_format_now_accepted(self):
        """
        Test that the original error format '22/06/2025 07:32:00' is now accepted
        when using a past date (the original issue was the format, not the future date)
        """
        test_image = self.create_test_image()
        # Use the exact format from the original error but with a past date
        past_date = timezone.now() - timezone.timedelta(days=1)
        datetime_str = past_date.strftime('%d/%m/%Y %H:%M:%S')  # Brazilian format from error

        form_data = {
            'description': 'Test photo - original error format',
            'event_datetime': datetime_str,
            'caption': 'Testing the fix for the original browser console error'
        }
        form = PhotoCreateForm(
            data=form_data,
            files={'image': test_image},
            patient=self.patient,
            user=self.user
        )

        # This should now pass - the original error was about format, not validation
        self.assertTrue(
            form.is_valid(),
            f"The original error format '{datetime_str}' should now be accepted. Errors: {form.errors}"
        )

    def test_html5_datetime_local_format_works(self):
        """Test that HTML5 datetime-local format works correctly"""
        test_image = self.create_test_image()
        past_date = timezone.now() - timezone.timedelta(days=1)
        datetime_str = past_date.strftime('%Y-%m-%dT%H:%M')  # HTML5 format

        form_data = {
            'description': 'Test photo - HTML5 format',
            'event_datetime': datetime_str,
            'caption': 'Testing HTML5 datetime-local format'
        }
        form = PhotoCreateForm(
            data=form_data,
            files={'image': test_image},
            patient=self.patient,
            user=self.user
        )

        self.assertTrue(
            form.is_valid(),
            f"HTML5 datetime-local format '{datetime_str}' should work. Errors: {form.errors}"
        )

    def test_form_initial_value_is_html5_compatible(self):
        """Test that form initial values are HTML5 datetime-local compatible"""
        form = PhotoCreateForm(patient=self.patient, user=self.user)
        initial_value = form.fields['event_datetime'].initial

        # Should match HTML5 datetime-local format: YYYY-MM-DDTHH:MM
        self.assertIsNotNone(initial_value)
        self.assertRegex(
            initial_value,
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',
            f"Initial value '{initial_value}' should be in HTML5 datetime-local format"
        )


class FormSecurityTests(TestCase):
    """Tests for form security and validation"""

    def setUp(self):
        """Set up test data"""
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')

        # Load malicious test files
        with open(os.path.join(self.test_media_dir, 'malicious.jpg'), 'rb') as f:
            self.malicious_image_content = f.read()

        with open(os.path.join(self.test_media_dir, 'polyglot.jpg'), 'rb') as f:
            self.polyglot_content = f.read()

    def test_malicious_file_rejection(self):
        """Test rejection of malicious files"""
        # TODO: Implement when forms are available
        pass

    def test_file_extension_spoofing_detection(self):
        """Test detection of file extension spoofing"""
        # TODO: Implement when forms are available
        pass

    def test_mime_type_validation(self):
        """Test MIME type validation"""
        # TODO: Implement when forms are available
        pass

    def test_file_content_validation(self):
        """Test file content validation (magic number checking)"""
        # TODO: Implement when forms are available
        pass


class FormIntegrationTests(TestCase):
    """Tests for form integration with other components"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test hospital

        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            
            created_by=self.user,
            updated_by=self.user
        )

    def test_form_patient_association(self):
        """Test form association with patients"""
        # TODO: Implement when forms are available
        pass

    def test_form_user_permissions(self):
        """Test form user permissions"""
        # TODO: Implement when forms are available
        pass

    def test_form_hospital_context(self):
        """Test form hospital context"""
        # TODO: Implement when forms are available
        pass
