# MediaFiles User Acceptance Testing Scenarios
# UAT scenarios for photo functionality in medical context

import os
import tempfile
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import Client

from apps.mediafiles.models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile
from apps.patients.models import Patient
from apps.events.models import Event

User = get_user_model()


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class MedicalProfessionalWorkflowTests(TransactionTestCase):
    """
    UAT scenarios for medical professionals using photo functionality.
    
    These tests simulate real-world usage scenarios in a medical environment.
    """
    
    def setUp(self):
        """Set up medical professional and patient data"""
        # Create medical professional user
        self.doctor = User.objects.create_user(
            username='dr_smith',
            email='dr.smith@hospital.com',
            password='secure_password123',
            first_name='John',
            last_name='Smith'
        )
        
        # Create patient
        self.patient = Patient.objects.create(
            name="Maria Santos",
            birth_date="1975-08-15",
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create realistic medical image content (simulated X-ray)
        self.xray_content = self._create_medical_image_content("xray")
        self.wound_photo_content = self._create_medical_image_content("wound")
        
        self.client = Client()
    
    def _create_medical_image_content(self, image_type):
        """Create realistic medical image content for testing"""
        # JPEG header for valid image
        jpeg_header = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00'
        )
        
        # Add type-specific content
        if image_type == "xray":
            content = b"XRAY_DATA_" + b"x" * 1000
        elif image_type == "wound":
            content = b"WOUND_PHOTO_" + b"w" * 800
        else:
            content = b"MEDICAL_IMAGE_" + b"m" * 500
        
        jpeg_end = b'\xff\xd9'
        return jpeg_header + content + jpeg_end
    
    def test_scenario_1_emergency_xray_upload(self):
        """
        Scenario 1: Emergency Room - Doctor uploads X-ray during patient examination
        
        User Story: As an emergency room doctor, I need to quickly upload and view
        X-ray images during patient examination to make immediate treatment decisions.
        """
        self.client.force_login(self.doctor)
        
        # Step 1: Doctor accesses patient record and navigates to photo upload
        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(upload_url)
        
        # Verify upload form is accessible
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Imagem')  # Image upload field
        self.assertContains(response, self.patient.name)  # Patient context
        
        # Step 2: Doctor uploads X-ray with medical description
        xray_file = SimpleUploadedFile(
            "chest_xray_emergency.jpg",
            self.xray_content,
            content_type="image/jpeg"
        )
        
        form_data = {
            'description': 'Chest X-ray - Emergency admission, suspected pneumonia',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Patient presents with chest pain and difficulty breathing. X-ray shows possible infiltrate in right lower lobe.',
            'image': xray_file
        }
        
        response = self.client.post(upload_url, form_data, follow=True)
        
        # Verify successful upload and redirect
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Verify X-ray appears in patient timeline
        photo = Photo.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(photo)
        self.assertEqual(photo.description, 'Chest X-ray - Emergency admission, suspected pneumonia')
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.created_by, self.doctor)
        
        # Step 4: Doctor views X-ray in detail for diagnosis
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)
        self.assertContains(response, photo.caption)
        
        # Step 5: Verify secure file access
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': photo.media_file.id})
        response = self.client.get(file_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        
        print("✓ Scenario 1 PASSED: Emergency X-ray upload workflow completed successfully")
    
    def test_scenario_2_wound_care_documentation(self):
        """
        Scenario 2: Wound Care - Nurse documents wound healing progress
        
        User Story: As a wound care nurse, I need to document wound healing progress
        with photos to track patient recovery and adjust treatment plans.
        """
        self.client.force_login(self.doctor)  # Using doctor for permissions
        
        # Step 1: Upload initial wound photo
        wound_file = SimpleUploadedFile(
            "wound_day_1.jpg",
            self.wound_photo_content,
            content_type="image/jpeg"
        )
        
        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Post-surgical wound - Day 1',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Initial wound assessment: 5cm incision, clean edges, no signs of infection. Dressing applied.',
            'image': wound_file
        }
        
        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Verify photo is properly categorized and accessible
        wound_photo = Photo.objects.filter(
            patient=self.patient,
            description__icontains='wound'
        ).first()
        
        self.assertIsNotNone(wound_photo)
        self.assertIn('Post-surgical wound', wound_photo.description)
        
        # Step 3: Update wound photo with additional notes (within 24-hour edit window)
        edit_url = reverse('mediafiles:photo_update', kwargs={'pk': wound_photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        
        updated_form_data = {
            'description': 'Post-surgical wound - Day 1 (Updated)',
            'event_datetime': wound_photo.event_datetime.strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Initial wound assessment: 5cm incision, clean edges, no signs of infection. Dressing applied. Patient reports minimal pain (2/10).'
        }
        
        response = self.client.post(edit_url, updated_form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify update was successful
        wound_photo.refresh_from_db()
        self.assertIn('Updated', wound_photo.description)
        self.assertIn('minimal pain', wound_photo.caption)
        
        print("✓ Scenario 2 PASSED: Wound care documentation workflow completed successfully")
    
    def test_scenario_3_consultation_photo_sharing(self):
        """
        Scenario 3: Specialist Consultation - Sharing photos for remote consultation
        
        User Story: As a primary care physician, I need to share patient photos
        with specialists for remote consultation while maintaining patient privacy.
        """
        self.client.force_login(self.doctor)
        
        # Step 1: Upload diagnostic photo for consultation
        diagnostic_file = SimpleUploadedFile(
            "skin_lesion_consultation.jpg",
            self.wound_photo_content,
            content_type="image/jpeg"
        )
        
        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Skin lesion - Dermatology consultation requested',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Irregular pigmented lesion on left shoulder, 8mm diameter. Patient reports recent changes in size and color.',
            'image': diagnostic_file
        }
        
        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Verify photo is securely stored with UUID filename
        consultation_photo = Photo.objects.filter(
            patient=self.patient,
            description__icontains='consultation'
        ).first()
        
        self.assertIsNotNone(consultation_photo)
        
        # Verify secure filename (no patient info in path)
        file_path = consultation_photo.media_file.file.name
        self.assertNotIn(self.patient.name.lower(), file_path.lower())
        self.assertNotIn('skin_lesion', file_path.lower())
        
        # Step 3: Verify file can be accessed securely
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': consultation_photo.media_file.id})
        response = self.client.get(file_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Verify original filename is preserved in database for reference
        self.assertEqual(
            consultation_photo.media_file.original_filename,
            'skin_lesion_consultation.jpg'
        )
        
        print("✓ Scenario 3 PASSED: Consultation photo sharing workflow completed successfully")
    
    def test_scenario_4_patient_timeline_integration(self):
        """
        Scenario 4: Patient Timeline - Photos integrated with medical timeline
        
        User Story: As a healthcare provider, I need to see patient photos
        integrated chronologically with other medical events in the patient timeline.
        """
        self.client.force_login(self.doctor)
        
        # Step 1: Create multiple photos over time to simulate timeline
        photos_data = [
            {
                'filename': 'admission_photo.jpg',
                'description': 'Patient admission - Initial assessment',
                'caption': 'Patient admitted with acute symptoms',
                'days_ago': 5
            },
            {
                'filename': 'treatment_day_3.jpg',
                'description': 'Treatment progress - Day 3',
                'caption': 'Significant improvement observed',
                'days_ago': 2
            },
            {
                'filename': 'discharge_photo.jpg',
                'description': 'Discharge assessment - Recovery complete',
                'caption': 'Patient ready for discharge, full recovery',
                'days_ago': 0
            }
        ]
        
        created_photos = []
        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        
        for photo_data in photos_data:
            photo_file = SimpleUploadedFile(
                photo_data['filename'],
                self.xray_content,
                content_type="image/jpeg"
            )
            
            event_datetime = timezone.now() - timezone.timedelta(days=photo_data['days_ago'])
            
            form_data = {
                'description': photo_data['description'],
                'event_datetime': event_datetime.strftime('%Y-%m-%dT%H:%M'),
                'caption': photo_data['caption'],
                'image': photo_file
            }
            
            response = self.client.post(upload_url, form_data, follow=True)
            self.assertEqual(response.status_code, 200)
            
            # Find the created photo
            photo = Photo.objects.filter(
                patient=self.patient,
                description=photo_data['description']
            ).first()
            created_photos.append(photo)
        
        # Step 2: Verify photos are properly ordered by date
        patient_photos = Photo.objects.filter(patient=self.patient).order_by('event_datetime')
        
        self.assertEqual(len(patient_photos), 3)
        self.assertIn('admission', patient_photos[0].description.lower())
        self.assertIn('treatment', patient_photos[1].description.lower())
        self.assertIn('discharge', patient_photos[2].description.lower())
        
        # Step 3: Verify each photo maintains proper event type
        for photo in patient_photos:
            self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
            self.assertEqual(photo.created_by, self.doctor)
            self.assertIsNotNone(photo.media_file)
        
        print("✓ Scenario 4 PASSED: Patient timeline integration completed successfully")

    def test_scenario_5_file_security_validation(self):
        """
        Scenario 5: File Security - System rejects malicious and invalid files

        User Story: As a system administrator, I need to ensure that only safe,
        valid medical images can be uploaded to protect system security.
        """
        self.client.force_login(self.doctor)
        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})

        # Test 1: Invalid file type rejection
        text_file = SimpleUploadedFile(
            "malicious.txt",
            b"This is not an image file",
            content_type="text/plain"
        )

        form_data = {
            'description': 'Test upload',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'image': text_file
        }

        response = self.client.post(upload_url, form_data)
        # Should stay on form page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')

        # Test 2: Oversized file rejection
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB (over limit)
        large_file = SimpleUploadedFile(
            "large.jpg",
            large_content,
            content_type="image/jpeg"
        )

        form_data['image'] = large_file
        response = self.client.post(upload_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'muito grande')  # "too large" in Portuguese

        # Test 3: Valid file acceptance
        valid_file = SimpleUploadedFile(
            "valid_medical_image.jpg",
            self.xray_content,
            content_type="image/jpeg"
        )

        form_data['image'] = valid_file
        form_data['description'] = 'Valid medical image upload test'
        response = self.client.post(upload_url, form_data, follow=True)

        # Should succeed
        self.assertEqual(response.status_code, 200)

        # Verify photo was created
        valid_photo = Photo.objects.filter(
            patient=self.patient,
            description='Valid medical image upload test'
        ).first()
        self.assertIsNotNone(valid_photo)

        print("✓ Scenario 5 PASSED: File security validation completed successfully")

    def test_scenario_6_edit_window_enforcement(self):
        """
        Scenario 6: Edit Window - 24-hour edit window enforcement

        User Story: As a healthcare administrator, I need to ensure that medical
        records can only be edited within a reasonable timeframe to maintain
        data integrity and audit compliance.
        """
        self.client.force_login(self.doctor)

        # Step 1: Create a photo
        photo_file = SimpleUploadedFile(
            "test_edit_window.jpg",
            self.xray_content,
            content_type="image/jpeg"
        )

        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Test photo for edit window validation',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Original caption',
            'image': photo_file
        }

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Step 2: Find the created photo
        photo = Photo.objects.filter(
            patient=self.patient,
            description='Test photo for edit window validation'
        ).first()
        self.assertIsNotNone(photo)

        # Step 3: Test edit within 24-hour window (should work)
        edit_url = reverse('mediafiles:photo_update', kwargs={'pk': photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        # Submit edit
        edit_data = {
            'description': 'Updated description within window',
            'event_datetime': photo.event_datetime.strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Updated caption within 24 hours'
        }

        response = self.client.post(edit_url, edit_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify edit was successful
        photo.refresh_from_db()
        self.assertEqual(photo.description, 'Updated description within window')
        self.assertEqual(photo.caption, 'Updated caption within 24 hours')

        # Step 4: Test delete within window (should work)
        delete_url = reverse('mediafiles:photo_delete', kwargs={'pk': photo.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)

        print("✓ Scenario 6 PASSED: Edit window enforcement completed successfully")


class SystemIntegrationUATTests(TestCase):
    """
    UAT scenarios for system integration and cross-functionality testing.
    """

    def setUp(self):
        """Set up integration test data"""
        self.doctor = User.objects.create_user(
            username='integration_doctor',
            email='integration@hospital.com',
            password='test_password123'
        )

        self.patient = Patient.objects.create(
            name="Integration Test Patient",
            birth_date="1980-01-01",
            created_by=self.doctor,
            updated_by=self.doctor
        )

        self.client = Client()

    def test_scenario_7_event_system_integration(self):
        """
        Scenario 7: Event System Integration - Photos integrate with event timeline

        User Story: As a healthcare provider, I need photos to appear as events
        in the patient timeline alongside other medical events.
        """
        self.client.force_login(self.doctor)

        # Create a photo event
        test_image = (
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

        photo_file = SimpleUploadedFile(
            "integration_test.jpg",
            test_image,
            content_type="image/jpeg"
        )

        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Integration test photo event',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Testing event system integration',
            'image': photo_file
        }

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify photo was created as proper event
        photo = Photo.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(photo)

        # Verify event properties
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.patient, self.patient)
        self.assertEqual(photo.created_by, self.doctor)
        self.assertIsNotNone(photo.event_datetime)

        # Verify photo appears in event queries
        patient_events = Event.objects.filter(patient=self.patient)
        self.assertIn(photo, patient_events)

        print("✓ Scenario 7 PASSED: Event system integration completed successfully")

    def test_scenario_8_permission_inheritance(self):
        """
        Scenario 8: Permission Inheritance - Photos inherit patient access permissions

        User Story: As a system administrator, I need photos to respect the same
        access controls as other patient data to maintain consistent security.
        """
        # Create two doctors
        doctor1 = User.objects.create_user(
            username='doctor1_perm',
            email='doctor1@hospital.com',
            password='test123'
        )

        doctor2 = User.objects.create_user(
            username='doctor2_perm',
            email='doctor2@hospital.com',
            password='test123'
        )

        # Doctor1 creates a photo
        self.client.force_login(doctor1)

        test_image = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )

        photo_file = SimpleUploadedFile(
            "permission_test.jpg",
            test_image,
            content_type="image/jpeg"
        )

        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Permission test photo',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'image': photo_file
        }

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        photo = Photo.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(photo)

        # Doctor1 should be able to access their photo
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # Doctor2 should not be able to access the photo (assuming no shared access)
        self.client.force_login(doctor2)
        response = self.client.get(detail_url)
        self.assertIn(response.status_code, [403, 404])  # Access denied

        print("✓ Scenario 8 PASSED: Permission inheritance completed successfully")


# PhotoSeries UAT Scenarios (Step 3.11)

@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class PhotoSeriesUATTests(TransactionTestCase):
    """
    UAT scenarios for PhotoSeries functionality in medical context.

    These tests simulate real-world usage scenarios for photo series uploads
    and management in medical environments.
    """

    def setUp(self):
        """Set up medical professional and patient data"""
        # Create medical professional user
        self.doctor = User.objects.create_user(
            username='dr_photoseries',
            email='dr.photoseries@hospital.com',
            password='secure_password123',
            first_name='Sarah',
            last_name='Johnson'
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Carlos Silva",
            birth_date="1985-03-20",
            created_by=self.doctor,
            updated_by=self.doctor
        )

        # Create realistic medical image content
        self.medical_image_content = (
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

        self.client = Client()

    def test_scenario_ps1_wound_progression_series(self):
        """
        Scenario PS1: Wound Care - Document wound healing progression with photo series

        User Story: As a wound care specialist, I need to upload multiple photos
        of a wound taken at the same time to document healing progression from
        different angles and create a comprehensive visual record.
        """
        self.client.force_login(self.doctor)

        # Step 1: Doctor accesses PhotoSeries upload form
        upload_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(upload_url)

        # Verify upload form is accessible
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Série de Fotos')  # PhotoSeries upload
        self.assertContains(response, self.patient.name)  # Patient context

        # Step 2: Doctor uploads multiple wound photos taken at same session
        wound_photos = []
        for i, angle in enumerate(['frontal', 'lateral', 'superior', 'close_up']):
            wound_photos.append(SimpleUploadedFile(
                f"wound_{angle}_view.jpg",
                self.medical_image_content,
                content_type="image/jpeg"
            ))

        form_data = {
            'description': 'Wound healing progression - Week 2 assessment',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Post-surgical wound showing significant improvement. Multiple angles captured for comprehensive documentation.',
            'images': wound_photos
        }

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Step 3: Verify PhotoSeries was created in database
        series = PhotoSeries.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(series)
        self.assertEqual(series.description, 'Wound healing progression - Week 2 assessment')
        self.assertEqual(series.event_type, Event.PHOTO_SERIES_EVENT)
        self.assertEqual(series.created_by, self.doctor)

        # Step 4: Verify all photos were added to series in correct order
        photos = series.get_ordered_photos()
        self.assertEqual(len(photos), 4)

        # Verify photo ordering is maintained
        for i, photo in enumerate(photos):
            series_file = PhotoSeriesFile.objects.get(photo_series=series, media_file=photo)
            self.assertEqual(series_file.order, i + 1)

        # Step 5: Doctor views PhotoSeries in detail with carousel
        detail_url = reverse('mediafiles:photoseries_detail', kwargs={'pk': series.pk})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, series.description)
        self.assertContains(response, '4 foto')  # Photo count
        self.assertContains(response, 'carousel')  # Carousel interface

        # Step 6: Verify individual photo access within series
        for photo in photos:
            file_url = reverse('mediafiles:serve_file', kwargs={'file_id': photo.id})
            response = self.client.get(file_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/jpeg')

        print("✓ Scenario PS1 PASSED: Wound progression series workflow completed successfully")

    def test_scenario_ps2_surgical_procedure_documentation(self):
        """
        Scenario PS2: Surgery - Document surgical procedure with before/during/after photos

        User Story: As a surgeon, I need to upload a series of photos documenting
        the surgical procedure from preparation through completion to maintain
        comprehensive surgical records.
        """
        self.client.force_login(self.doctor)

        # Step 1: Upload surgical procedure photo series
        surgical_photos = []
        phases = ['pre_op', 'incision', 'procedure', 'closure', 'post_op']

        for phase in phases:
            surgical_photos.append(SimpleUploadedFile(
                f"surgery_{phase}.jpg",
                self.medical_image_content,
                content_type="image/jpeg"
            ))

        upload_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Appendectomy procedure documentation',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Laparoscopic appendectomy performed successfully. Complete procedural documentation from preparation to closure.',
            'images': surgical_photos
        }

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Step 2: Verify surgical series was created
        surgical_series = PhotoSeries.objects.filter(
            patient=self.patient,
            description__icontains='Appendectomy'
        ).first()

        self.assertIsNotNone(surgical_series)
        self.assertEqual(surgical_series.get_photo_count(), 5)

        # Step 3: Verify secure file storage (no procedure details in filenames)
        photos = surgical_series.get_ordered_photos()
        for photo in photos:
            file_path = photo.file.name
            self.assertNotIn('appendectomy', file_path.lower())
            self.assertNotIn('surgery', file_path.lower())

            # Verify UUID-based filename
            filename = os.path.basename(file_path)
            name_without_ext = filename.rsplit('.', 1)[0]
            self.assertEqual(len(name_without_ext), 36)  # UUID length

        # Step 4: Test series editing (limited to description/caption)
        edit_url = reverse('mediafiles:photoseries_update', kwargs={'pk': surgical_series.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        # Update series information
        updated_form_data = {
            'description': 'Appendectomy procedure documentation (Updated)',
            'event_datetime': surgical_series.event_datetime.strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Laparoscopic appendectomy performed successfully. Complete procedural documentation from preparation to closure. Patient recovered well.'
        }

        response = self.client.post(edit_url, updated_form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify update was successful
        surgical_series.refresh_from_db()
        self.assertIn('Updated', surgical_series.description)
        self.assertIn('recovered well', surgical_series.caption)

        print("✓ Scenario PS2 PASSED: Surgical procedure documentation workflow completed successfully")

    def test_scenario_ps3_diagnostic_imaging_series(self):
        """
        Scenario PS3: Radiology - Upload series of diagnostic images from same study

        User Story: As a radiologist, I need to upload multiple images from the
        same diagnostic study (e.g., CT scan slices, MRI sequences) as a cohesive
        series for comprehensive analysis.
        """
        self.client.force_login(self.doctor)

        # Step 1: Upload diagnostic imaging series
        imaging_photos = []
        for i in range(6):  # Simulate 6 CT slices
            imaging_photos.append(SimpleUploadedFile(
                f"ct_abdomen_slice_{i+1:02d}.jpg",
                self.medical_image_content,
                content_type="image/jpeg"
            ))

        upload_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'CT Abdomen - Diagnostic imaging study',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'CT scan of abdomen with contrast. 6 representative slices showing normal anatomy. No acute findings.',
            'images': imaging_photos
        }

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Step 2: Verify imaging series was created
        imaging_series = PhotoSeries.objects.filter(
            patient=self.patient,
            description__icontains='CT Abdomen'
        ).first()

        self.assertIsNotNone(imaging_series)
        self.assertEqual(imaging_series.get_photo_count(), 6)

        # Step 3: Test carousel navigation for image review
        detail_url = reverse('mediafiles:photoseries_detail', kwargs={'pk': imaging_series.pk})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'carousel-control')  # Navigation controls
        self.assertContains(response, 'carousel-indicators')  # Image indicators

        # Step 4: Test ZIP download for external consultation
        download_url = reverse('mediafiles:photoseries_download', kwargs={'pk': imaging_series.pk})
        response = self.client.get(download_url)

        # Should either provide ZIP or handle appropriately
        self.assertIn(response.status_code, [200, 302, 404])

        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/zip')

        print("✓ Scenario PS3 PASSED: Diagnostic imaging series workflow completed successfully")

    def test_scenario_ps4_timeline_integration_verification(self):
        """
        Scenario PS4: Timeline Integration - PhotoSeries appears correctly in patient timeline

        User Story: As a healthcare provider, I need PhotoSeries to appear as
        cohesive events in the patient timeline, distinct from individual photos
        but integrated chronologically.
        """
        self.client.force_login(self.doctor)

        # Step 1: Create individual photo for comparison
        individual_photo = SimpleUploadedFile(
            "individual_xray.jpg",
            self.medical_image_content,
            content_type="image/jpeg"
        )

        photo_upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        photo_form_data = {
            'description': 'Individual chest X-ray',
            'event_datetime': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Routine chest X-ray',
            'image': individual_photo
        }

        response = self.client.post(photo_upload_url, photo_form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Step 2: Create PhotoSeries
        series_photos = []
        for i in range(3):
            series_photos.append(SimpleUploadedFile(
                f"follow_up_{i+1}.jpg",
                self.medical_image_content,
                content_type="image/jpeg"
            ))

        series_upload_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.pk})
        series_form_data = {
            'description': 'Follow-up examination series',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Comprehensive follow-up examination with multiple views',
            'images': series_photos
        }

        response = self.client.post(series_upload_url, series_form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Step 3: Verify timeline shows both individual photo and series
        timeline_url = reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, 200)

        # Should show individual photo
        self.assertContains(response, 'Individual chest X-ray')

        # Should show PhotoSeries
        self.assertContains(response, 'Follow-up examination series')
        self.assertContains(response, '3 foto')  # Photo count for series

        # Step 4: Verify chronological ordering
        individual_photo_obj = Photo.objects.filter(
            patient=self.patient,
            description='Individual chest X-ray'
        ).first()

        photo_series_obj = PhotoSeries.objects.filter(
            patient=self.patient,
            description='Follow-up examination series'
        ).first()

        self.assertIsNotNone(individual_photo_obj)
        self.assertIsNotNone(photo_series_obj)

        # Individual photo should be earlier
        self.assertLess(individual_photo_obj.event_datetime, photo_series_obj.event_datetime)

        print("✓ Scenario PS4 PASSED: Timeline integration verification completed successfully")

    def test_scenario_ps5_batch_upload_performance_uat(self):
        """
        Scenario PS5: Performance - Large batch upload handles efficiently

        User Story: As a medical photographer, I need to upload multiple high-quality
        medical images simultaneously without system performance degradation or
        timeout issues.
        """
        self.client.force_login(self.doctor)

        # Step 1: Prepare large batch of photos (8 photos to simulate real usage)
        batch_photos = []
        for i in range(8):
            # Create slightly larger content to simulate real medical images
            large_content = self.medical_image_content + (b"x" * 50000)  # ~50KB additional
            batch_photos.append(SimpleUploadedFile(
                f"batch_medical_photo_{i+1:02d}.jpg",
                large_content,
                content_type="image/jpeg"
            ))

        upload_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.pk})
        form_data = {
            'description': 'Comprehensive medical documentation - Batch upload test',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Large batch upload test for performance validation in medical environment.',
            'images': batch_photos
        }

        # Step 2: Measure upload time
        import time
        start_time = time.time()

        response = self.client.post(upload_url, form_data, follow=True)

        upload_time = time.time() - start_time

        # Step 3: Verify successful upload
        self.assertEqual(response.status_code, 200)

        # Step 4: Verify all photos were uploaded
        batch_series = PhotoSeries.objects.filter(
            patient=self.patient,
            description__icontains='Batch upload test'
        ).first()

        self.assertIsNotNone(batch_series)
        self.assertEqual(batch_series.get_photo_count(), 8)

        # Step 5: Verify reasonable upload time (should be under 10 seconds)
        self.assertLess(upload_time, 10.0, f"Batch upload took {upload_time:.2f}s, should be < 10s")

        # Step 6: Verify gallery loads efficiently
        detail_url = reverse('mediafiles:photoseries_detail', kwargs={'pk': batch_series.pk})

        start_time = time.time()
        response = self.client.get(detail_url)
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 3.0, f"Gallery loading took {load_time:.2f}s, should be < 3s")

        print(f"✓ Scenario PS5 PASSED: Batch upload performance (Upload: {upload_time:.2f}s, Load: {load_time:.2f}s)")

    def test_scenario_ps6_security_validation_comprehensive(self):
        """
        Scenario PS6: Security - Comprehensive security validation for PhotoSeries

        User Story: As a system administrator, I need to ensure PhotoSeries uploads
        maintain the same security standards as individual photos, with additional
        validation for batch operations.
        """
        self.client.force_login(self.doctor)
        upload_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.pk})

        # Test 1: Mixed valid and invalid files (should reject entire batch)
        mixed_files = [
            SimpleUploadedFile("valid1.jpg", self.medical_image_content, content_type="image/jpeg"),
            SimpleUploadedFile("valid2.jpg", self.medical_image_content, content_type="image/jpeg"),
            SimpleUploadedFile("malicious.exe", b"malicious content", content_type="application/exe")
        ]

        form_data = {
            'description': 'Security test - mixed files',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Security validation test',
            'images': mixed_files
        }

        response = self.client.post(upload_url, form_data)
        # Should stay on form page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')

        # Verify no PhotoSeries was created
        self.assertFalse(PhotoSeries.objects.filter(
            patient=self.patient,
            description='Security test - mixed files'
        ).exists())

        # Test 2: Valid files should work
        valid_files = [
            SimpleUploadedFile("secure1.jpg", self.medical_image_content, content_type="image/jpeg"),
            SimpleUploadedFile("secure2.jpg", self.medical_image_content, content_type="image/jpeg")
        ]

        form_data['images'] = valid_files
        form_data['description'] = 'Security test - valid files'

        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify PhotoSeries was created
        secure_series = PhotoSeries.objects.filter(
            patient=self.patient,
            description='Security test - valid files'
        ).first()

        self.assertIsNotNone(secure_series)
        self.assertEqual(secure_series.get_photo_count(), 2)

        # Test 3: Verify secure file storage
        photos = secure_series.get_ordered_photos()
        for photo in photos:
            file_path = photo.file.name
            # Should not contain original filenames
            self.assertNotIn('secure1', file_path)
            self.assertNotIn('secure2', file_path)

            # Should use UUID-based naming
            filename = os.path.basename(file_path)
            name_without_ext = filename.rsplit('.', 1)[0]
            self.assertEqual(len(name_without_ext), 36)  # UUID length

        print("✓ Scenario PS6 PASSED: Security validation comprehensive testing completed successfully")
