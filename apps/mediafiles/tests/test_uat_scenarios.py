# MediaFiles User Acceptance Testing Scenarios
# UAT scenarios for photo/video functionality in medical context.
#
# Scenarios run through the current HTTP views and FilePond upload contract
# (TemporaryUpload rows + ``upload_id``/``upload_ids`` form fields). All data
# is synthetic; Hospital was removed in the single-hospital refactor.

import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.mediafiles.models import Photo, PhotoSeries

from .factories import (
    create_patient,
    create_user,
    load_test_image_bytes,
)

User = get_user_model()

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_uat_"))

FULL_EVENT_PERMS = (
    "events.add_event",
    "events.view_event",
    "events.change_event",
    "events.delete_event",
    "patients.view_patient",
)


def grant_permissions(user, *names):
    """Grant Django model permissions to a user (synthetic test fixture)."""
    for name in names:
        app_label, codename = name.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )


def past_datetime_str(hours=2):
    """HTML5 ``datetime-local`` value for a recent past instant."""
    return timezone.localtime(
        timezone.now() - timezone.timedelta(hours=hours)
    ).strftime("%Y-%m-%dT%H:%M")


def create_temp_upload(filename, content=None, content_type="image/jpeg"):
    """Create a FilePond TemporaryUpload row; return its upload_id."""
    import shortuuid
    from django_drf_filepond.models import TemporaryUpload

    content = load_test_image_bytes() if content is None else content
    upload_id = shortuuid.uuid()
    TemporaryUpload.objects.create(
        upload_id=upload_id,
        upload_name=filename,
        upload_type="F",
        file=SimpleUploadedFile(filename, content, content_type=content_type),
    )
    return upload_id


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MedicalProfessionalWorkflowTests(TransactionTestCase):
    """
    UAT scenarios for medical professionals using photo functionality.

    These tests simulate real-world usage scenarios in a medical environment.
    """

    def setUp(self):
        """Set up medical professional and patient data"""
        # Create medical professional user with the events permissions the
        # current views enforce
        self.doctor = create_user(
            username="dr_smith", first_name="John", last_name="Smith"
        )
        grant_permissions(self.doctor, *FULL_EVENT_PERMS)

        self.patient = create_patient(self.doctor, name="Maria Santos")

        self.client = Client()
        self.client.force_login(self.doctor)

    def upload_photo(self, filename, description, caption="", event_datetime=None):
        """Upload a photo through the current FilePond create view."""
        upload_id = create_temp_upload(filename)
        url = reverse("mediafiles:photo_create", kwargs={"patient_id": self.patient.pk})
        data = {
            "description": description,
            "event_datetime": (
                event_datetime.strftime("%Y-%m-%dT%H:%M")
                if event_datetime
                else past_datetime_str()
            ),
            "caption": caption,
            "upload_id": upload_id,
        }
        return self.client.post(url, data)

    def test_scenario_1_emergency_xray_upload(self):
        """
        Scenario 1: Emergency Room - Doctor uploads X-ray during patient examination

        User Story: As an emergency room doctor, I need to quickly upload and view
        X-ray images during patient examination to make immediate treatment decisions.
        """
        # Step 1: Doctor accesses patient record and navigates to photo upload
        upload_url = reverse(
            "mediafiles:photo_create", kwargs={"patient_id": self.patient.pk}
        )
        response = self.client.get(upload_url)

        # Verify upload form is accessible
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.name)  # Patient context

        # Step 2: Doctor uploads X-ray with medical description
        response = self.upload_photo(
            "chest_xray_emergency.jpg",
            "Chest X-ray - Emergency admission, suspected pneumonia",
            caption=(
                "Patient presents with chest pain and difficulty breathing. "
                "X-ray shows possible infiltrate in right lower lobe."
            ),
        )

        # Verify successful upload and redirect to the patient timeline
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            ),
        )

        # Step 3: Verify X-ray appears as a photo event
        photo = Photo.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(photo)
        self.assertEqual(
            photo.description,
            "Chest X-ray - Emergency admission, suspected pneumonia",
        )
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.created_by, self.doctor)
        self.assertIsNotNone(photo.file_id)

        # Step 4: Doctor views X-ray in detail for diagnosis
        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)
        self.assertContains(response, photo.caption)

        # Step 5: Verify secure file access
        file_url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        response = self.client.get(file_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_scenario_2_wound_care_documentation(self):
        """
        Scenario 2: Wound Care - Nurse documents wound healing progress

        User Story: As a wound care nurse, I need to document wound healing progress
        with photos to track patient recovery and adjust treatment plans.
        """
        # Step 1: Upload initial wound photo
        response = self.upload_photo(
            "wound_day_1.jpg",
            "Post-surgical wound - Day 1",
            caption=(
                "Initial wound assessment: 5cm incision, clean edges, no signs "
                "of infection. Dressing applied."
            ),
        )
        self.assertEqual(response.status_code, 302)

        # Step 2: Verify photo is properly categorized and accessible
        wound_photo = Photo.objects.filter(
            patient=self.patient, description__icontains="wound"
        ).first()
        self.assertIsNotNone(wound_photo)
        self.assertIn("Post-surgical wound", wound_photo.description)

        # Step 3: Update wound photo with additional notes (within 24h window)
        edit_url = reverse("mediafiles:photo_update", kwargs={"pk": wound_photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        updated_form_data = {
            "description": "Post-surgical wound - Day 1 (Updated)",
            "event_datetime": timezone.localtime(wound_photo.event_datetime).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "caption": (
                "Initial wound assessment: 5cm incision, clean edges, no signs "
                "of infection. Dressing applied. Patient reports minimal pain (2/10)."
            ),
        }
        response = self.client.post(edit_url, updated_form_data)
        self.assertEqual(response.status_code, 302)

        # Verify update was successful
        wound_photo.refresh_from_db()
        self.assertIn("Updated", wound_photo.description)
        self.assertIn("minimal pain", wound_photo.caption)

    def test_scenario_3_consultation_photo_sharing(self):
        """
        Scenario 3: Specialist Consultation - Sharing photos for remote consultation

        User Story: As a primary care physician, I need to share patient photos
        with specialists for remote consultation while maintaining patient privacy.
        """
        # Step 1: Upload diagnostic photo for consultation
        response = self.upload_photo(
            "skin_lesion_consultation.jpg",
            "Skin lesion - Dermatology consultation requested",
            caption=(
                "Irregular pigmented lesion on left shoulder, 8mm diameter. "
                "Patient reports recent changes in size and color."
            ),
        )
        self.assertEqual(response.status_code, 302)

        # Step 2: Verify photo is stored with a UUID-based path
        consultation_photo = Photo.objects.filter(
            patient=self.patient, description__icontains="consultation"
        ).first()
        self.assertIsNotNone(consultation_photo)

        # Verify secure storage: no patient info or filename in the path
        original_dir = (
            Path(settings.MEDIA_ROOT)
            / f"photos/{consultation_photo.created_at.strftime('%Y/%m')}/originals"
        )
        stored_file = original_dir / f"{consultation_photo.file_id}.jpg"
        self.assertTrue(stored_file.exists())
        file_path = str(stored_file)
        self.assertNotIn(self.patient.name.lower(), file_path.lower())
        self.assertNotIn("skin_lesion", file_path.lower())

        # Step 3: Verify file can be accessed securely
        file_url = reverse(
            "mediafiles:serve_file",
            kwargs={"file_id": consultation_photo.file_id},
        )
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 200)

        # Step 4: Verify original filename is preserved in database for reference
        self.assertEqual(
            consultation_photo.original_filename, "skin_lesion_consultation.jpg"
        )

    def test_scenario_4_patient_timeline_integration(self):
        """
        Scenario 4: Patient Timeline - Photos integrated with medical timeline

        User Story: As a healthcare provider, I need to see patient photos
        integrated chronologically with other medical events in the patient timeline.
        """
        # Step 1: Create multiple photos over time to simulate timeline
        photos_data = [
            {
                "filename": "admission_photo.jpg",
                "description": "Patient admission - Initial assessment",
                "days_ago": 5,
            },
            {
                "filename": "treatment_day_3.jpg",
                "description": "Treatment progress - Day 3",
                "days_ago": 2,
            },
            {
                "filename": "discharge_photo.jpg",
                "description": "Discharge assessment - Recovery complete",
                "days_ago": 0,
            },
        ]

        for photo_data in photos_data:
            event_datetime = timezone.localtime(
                timezone.now() - timezone.timedelta(days=photo_data["days_ago"])
            )
            response = self.upload_photo(
                photo_data["filename"],
                photo_data["description"],
                event_datetime=event_datetime,
            )
            self.assertEqual(response.status_code, 302)

        # Step 2: Verify photos are properly ordered by date
        patient_photos = list(
            Photo.objects.filter(patient=self.patient).order_by("event_datetime")
        )
        self.assertEqual(len(patient_photos), 3)
        self.assertIn("admission", patient_photos[0].description.lower())
        self.assertIn("treatment", patient_photos[1].description.lower())
        self.assertIn("discharge", patient_photos[2].description.lower())

        # Step 3: Verify each photo maintains proper event type
        for photo in patient_photos:
            self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
            self.assertEqual(photo.created_by, self.doctor)
            self.assertIsNotNone(photo.file_id)

        # Step 4: The timeline page renders the photos chronologically
        timeline_url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient admission - Initial assessment")
        self.assertContains(response, "Discharge assessment - Recovery complete")

    def test_scenario_5_file_security_validation(self):
        """
        Scenario 5: File Security - System rejects malicious and invalid files

        User Story: As a system administrator, I need to ensure that only safe,
        valid medical images can be uploaded to protect system security.
        """
        upload_url = reverse(
            "mediafiles:photo_create", kwargs={"patient_id": self.patient.pk}
        )

        # Test 1: Non-image file rejection (FilePond form extension check)
        invalid_upload_id = create_temp_upload("malicious.txt")
        form_data = {
            "description": "Test upload",
            "event_datetime": past_datetime_str(),
            "caption": "",
            "upload_id": invalid_upload_id,
        }
        response = self.client.post(upload_url, form_data)
        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_id", response.context["form"].errors)
        self.assertFalse(Photo.objects.filter(patient=self.patient).exists())

        # Test 2: Unknown/expired upload id rejection
        form_data["upload_id"] = "x" * 22
        response = self.client.post(upload_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Photo.objects.filter(patient=self.patient).exists())

        # Test 3: Valid file acceptance
        valid_upload_id = create_temp_upload("valid_medical_image.jpg")
        form_data["upload_id"] = valid_upload_id
        form_data["description"] = "Valid medical image upload test"
        response = self.client.post(upload_url, form_data)
        self.assertEqual(response.status_code, 302)

        # Verify photo was created
        valid_photo = Photo.objects.filter(
            patient=self.patient, description="Valid medical image upload test"
        ).first()
        self.assertIsNotNone(valid_photo)

    def test_scenario_6_edit_window_enforcement(self):
        """
        Scenario 6: Edit Window - 24-hour edit window enforcement

        User Story: As a healthcare administrator, I need to ensure that medical
        records can only be edited within a reasonable timeframe to maintain
        data integrity and audit compliance.
        """
        # Step 1: Create a photo
        response = self.upload_photo(
            "test_edit_window.jpg",
            "Test photo for edit window validation",
            caption="Original caption",
        )
        self.assertEqual(response.status_code, 302)

        photo = Photo.objects.filter(
            patient=self.patient,
            description="Test photo for edit window validation",
        ).first()
        self.assertIsNotNone(photo)

        # Step 2: Edit within the 24-hour window (should work)
        edit_url = reverse("mediafiles:photo_update", kwargs={"pk": photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        edit_data = {
            "description": "Updated description within window",
            "event_datetime": timezone.localtime(photo.event_datetime).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "caption": "Updated caption within 24 hours",
        }
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)

        photo.refresh_from_db()
        self.assertEqual(photo.description, "Updated description within window")
        self.assertEqual(photo.caption, "Updated caption within 24 hours")

        # Step 3: Delete within window (should work)
        delete_url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)

        # Step 4: A second doctor cannot edit the photo (creator-only)
        other_doctor = create_user(username="dr_other")
        grant_permissions(other_doctor, *FULL_EVENT_PERMS)
        self.client.force_login(other_doctor)
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 403)


class SystemIntegrationUATTests(TestCase):
    """
    UAT scenarios for system integration and cross-functionality testing.
    """

    def setUp(self):
        """Set up integration test data"""
        self.doctor = create_user(username="integration_doctor")
        grant_permissions(self.doctor, *FULL_EVENT_PERMS)
        self.patient = create_patient(self.doctor, name="Integration Test Patient")

        self.client = Client()

    def test_scenario_7_event_system_integration(self):
        """
        Scenario 7: Event System Integration - Photos integrate with event timeline

        User Story: As a healthcare provider, I need photos to appear as events
        in the patient timeline alongside other medical events.
        """
        self.client.force_login(self.doctor)

        # Create a photo event directly through the current API (Photo row)
        photo = Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="integration_test.jpg",
            file_size=100,
            width=100,
            height=100,
            description="Integration test photo event",
            caption="Testing event system integration",
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )

        # Verify event properties
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.patient, self.patient)
        self.assertEqual(photo.created_by, self.doctor)
        self.assertIsNotNone(photo.event_datetime)

        # Verify photo appears in event queries (base Event rows)
        patient_events = Event.objects.filter(patient=self.patient)
        self.assertTrue(patient_events.filter(pk=photo.pk).exists())
        self.assertEqual(patient_events.get(pk=photo.pk).event_type, Event.PHOTO_EVENT)

        # And in the rendered patient timeline
        timeline_url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integration test photo event")

    def test_scenario_8_permission_inheritance(self):
        """
        Scenario 8: Permission Inheritance - Photos inherit patient access permissions

        User Story: As a system administrator, I need photos to respect the same
        access controls as other patient data to maintain consistent security.
        """
        # Create two doctors
        doctor1 = create_user(username="doctor1_perm")
        grant_permissions(doctor1, *FULL_EVENT_PERMS)

        doctor2 = create_user(username="doctor2_perm")

        # Doctor1 creates a photo
        self.client.force_login(doctor1)

        photo = Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="permission_test.jpg",
            file_size=100,
            width=100,
            height=100,
            description="Permission test photo",
            patient=self.patient,
            created_by=doctor1,
            updated_by=doctor1,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )

        # Doctor1 (with events.view_event) can access the photo
        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # Doctor2 without the events permission is denied (403)
        self.client.force_login(doctor2)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 403)


# PhotoSeries UAT Scenarios


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesUATTests(TransactionTestCase):
    """
    UAT scenarios for PhotoSeries functionality in medical context.

    These tests simulate real-world usage scenarios for photo series uploads
    and management in medical environments.
    """

    def setUp(self):
        """Set up medical professional and patient data"""
        self.doctor = create_user(
            username="dr_photoseries",
            first_name="Sarah",
            last_name="Johnson",
        )
        grant_permissions(self.doctor, *FULL_EVENT_PERMS)

        self.patient = create_patient(self.doctor, name="Carlos Silva")

        self.client = Client()
        self.client.force_login(self.doctor)

    def upload_series(self, filenames, description, caption=""):
        """Upload a photo series through the current FilePond create view."""
        upload_ids = ",".join([create_temp_upload(filename) for filename in filenames])
        url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.pk},
        )
        return self.client.post(
            url,
            {
                "description": description,
                "event_datetime": past_datetime_str(),
                "caption": caption,
                "upload_ids": upload_ids,
            },
        )

    def test_scenario_ps1_wound_progression_series(self):
        """
        Scenario PS1: Wound Care - Document wound healing progression with photo series

        User Story: As a wound care specialist, I need to upload multiple photos
        of a wound taken at the same time to document healing progression from
        different angles and create a comprehensive visual record.
        """
        # Step 1: Doctor accesses PhotoSeries upload form
        upload_url = reverse(
            "mediafiles:photoseries_create", kwargs={"patient_id": self.patient.pk}
        )
        response = self.client.get(upload_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Série de Fotos")
        self.assertContains(response, self.patient.name)

        # Step 2: Doctor uploads multiple wound photos taken at same session
        response = self.upload_series(
            [
                f"wound_{angle}_view.jpg"
                for angle in ("frontal", "lateral", "superior", "close_up")
            ],
            "Wound healing progression - Week 2 assessment",
            caption=(
                "Post-surgical wound showing significant improvement. Multiple "
                "angles captured for comprehensive documentation."
            ),
        )
        self.assertEqual(response.status_code, 302)

        # Step 3: Verify PhotoSeries was created in database
        series = PhotoSeries.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(series)
        self.assertEqual(
            series.description, "Wound healing progression - Week 2 assessment"
        )
        self.assertEqual(series.event_type, Event.PHOTO_SERIES_EVENT)
        self.assertEqual(series.created_by, self.doctor)

        # Step 4: Verify all photos were added to series in correct order
        photos = series.get_ordered_photos()
        self.assertEqual(photos.count(), 4)
        self.assertEqual([sf.order for sf in photos], [1, 2, 3, 4])

        # Step 5: Doctor views PhotoSeries in detail with gallery
        detail_url = reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, series.description)
        self.assertContains(response, "4 fotos")
        self.assertContains(response, "photo-gallery")

        # Step 6: Verify individual photo access within series
        for series_file in photos:
            file_url = reverse(
                "mediafiles:serve_file",
                kwargs={"file_id": series_file.file_id},
            )
            response = self.client.get(file_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_scenario_ps2_surgical_procedure_documentation(self):
        """
        Scenario PS2: Surgery - Document surgical procedure with before/during/after photos

        User Story: As a surgeon, I need to upload a series of photos documenting
        the surgical procedure from preparation through completion to maintain
        comprehensive surgical records.
        """
        # Step 1: Upload surgical procedure photo series
        phases = ["pre_op", "incision", "procedure", "closure", "post_op"]
        response = self.upload_series(
            [f"surgery_{phase}.jpg" for phase in phases],
            "Appendectomy procedure documentation",
            caption=(
                "Laparoscopic appendectomy performed successfully. Complete "
                "procedural documentation from preparation to closure."
            ),
        )
        self.assertEqual(response.status_code, 302)

        # Step 2: Verify surgical series was created
        surgical_series = PhotoSeries.objects.filter(
            patient=self.patient, description__icontains="Appendectomy"
        ).first()
        self.assertIsNotNone(surgical_series)
        self.assertEqual(surgical_series.get_photo_count(), 5)

        # Step 3: Verify secure file storage (no procedure details in paths)
        for series_file in surgical_series.get_ordered_photos():
            file_path = (
                Path(settings.MEDIA_ROOT)
                / f"photo_series/{surgical_series.created_at.strftime('%Y/%m')}/originals"
                / f"{series_file.file_id}.jpg"
            )
            self.assertTrue(file_path.exists())
            self.assertNotIn("appendectomy", str(file_path).lower())
            self.assertNotIn("surgery", str(file_path).lower())
            # UUID-based filename (36 chars without extension)
            filename = file_path.name.rsplit(".", 1)[0]
            self.assertEqual(len(filename), 36)

        # Step 4: Test series editing (limited to description/caption)
        edit_url = reverse(
            "mediafiles:photoseries_update", kwargs={"pk": surgical_series.pk}
        )
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        updated_form_data = {
            "description": "Appendectomy procedure documentation (Updated)",
            "event_datetime": timezone.localtime(
                surgical_series.event_datetime
            ).strftime("%Y-%m-%dT%H:%M"),
            "caption": (
                "Laparoscopic appendectomy performed successfully. Complete "
                "procedural documentation from preparation to closure. "
                "Patient recovered well."
            ),
        }
        response = self.client.post(edit_url, updated_form_data)
        self.assertEqual(response.status_code, 302)

        surgical_series.refresh_from_db()
        self.assertIn("Updated", surgical_series.description)
        self.assertIn("recovered well", surgical_series.caption)

    def test_scenario_ps3_diagnostic_imaging_series(self):
        """
        Scenario PS3: Radiology - Upload series of diagnostic images from same study

        User Story: As a radiologist, I need to upload multiple images from the
        same diagnostic study (e.g., CT scan slices, MRI sequences) as a cohesive
        series for comprehensive analysis.
        """
        # Step 1: Upload diagnostic imaging series (6 CT slices)
        response = self.upload_series(
            [f"ct_abdomen_slice_{i + 1:02d}.jpg" for i in range(6)],
            "CT Abdomen - Diagnostic imaging study",
            caption=(
                "CT scan of abdomen with contrast. 6 representative slices "
                "showing normal anatomy. No acute findings."
            ),
        )
        self.assertEqual(response.status_code, 302)

        # Step 2: Verify imaging series was created
        imaging_series = PhotoSeries.objects.filter(
            patient=self.patient, description__icontains="CT Abdomen"
        ).first()
        self.assertIsNotNone(imaging_series)
        self.assertEqual(imaging_series.get_photo_count(), 6)

        # Step 3: Review the series in the detail view
        detail_url = reverse(
            "mediafiles:photoseries_detail", kwargs={"pk": imaging_series.pk}
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CT Abdomen - Diagnostic imaging study")
        self.assertContains(response, "photo-gallery")

        # Step 4: ZIP download follows the current FilePond contract (302)
        download_url = reverse(
            "mediafiles:photoseries_download", kwargs={"pk": imaging_series.pk}
        )
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 302)

    def test_scenario_ps4_timeline_integration_verification(self):
        """
        Scenario PS4: Timeline Integration - PhotoSeries appears correctly in patient timeline

        User Story: As a healthcare provider, I need PhotoSeries to appear as
        cohesive events in the patient timeline, distinct from individual photos
        but integrated chronologically.
        """
        # Step 1: Create individual photo (one day ago)
        upload_id = create_temp_upload("individual_xray.jpg")
        photo_upload_url = reverse(
            "mediafiles:photo_create", kwargs={"patient_id": self.patient.pk}
        )
        response = self.client.post(
            photo_upload_url,
            {
                "description": "Individual chest X-ray",
                "event_datetime": (
                    timezone.now() - timezone.timedelta(days=1)
                ).strftime("%Y-%m-%dT%H:%M"),
                "caption": "Routine chest X-ray",
                "upload_id": upload_id,
            },
        )
        self.assertEqual(response.status_code, 302)

        # Step 2: Create PhotoSeries (now)
        response = self.upload_series(
            ["follow_up_1.jpg", "follow_up_2.jpg", "follow_up_3.jpg"],
            "Follow-up examination series",
            caption="Comprehensive follow-up examination with multiple views",
        )
        self.assertEqual(response.status_code, 302)

        # Step 3: Verify timeline shows both individual photo and series
        timeline_url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Individual chest X-ray")
        self.assertContains(response, "Follow-up examination series")

        # Step 4: Verify chronological ordering
        individual_photo_obj = Photo.objects.filter(
            patient=self.patient, description="Individual chest X-ray"
        ).first()
        photo_series_obj = PhotoSeries.objects.filter(
            patient=self.patient, description="Follow-up examination series"
        ).first()
        self.assertIsNotNone(individual_photo_obj)
        self.assertIsNotNone(photo_series_obj)
        self.assertLess(
            individual_photo_obj.event_datetime, photo_series_obj.event_datetime
        )

    def test_scenario_ps5_batch_upload_performance_uat(self):
        """
        Scenario PS5: Performance - Large batch upload handles efficiently

        User Story: As a medical photographer, I need to upload multiple high-quality
        medical images simultaneously without system performance degradation or
        timeout issues.
        """
        # Step 1: Prepare large batch of photos (8 photos)
        import time

        upload_ids = []
        for i in range(8):
            # Slightly larger synthetic content per photo
            content = load_test_image_bytes() + (b"x" * 50000)
            upload_ids.append(
                create_temp_upload(
                    f"batch_medical_photo_{i + 1:02d}.jpg", content=content
                )
            )

        upload_url = reverse(
            "mediafiles:photoseries_create", kwargs={"patient_id": self.patient.pk}
        )
        form_data = {
            "description": "Comprehensive medical documentation - Batch upload test",
            "event_datetime": past_datetime_str(),
            "caption": (
                "Large batch upload test for performance validation in medical environment."
            ),
            "upload_ids": ",".join(upload_ids),
        }

        # Step 2: Measure upload time
        start_time = time.time()
        response = self.client.post(upload_url, form_data)
        upload_time = time.time() - start_time

        # Step 3: Verify successful upload
        self.assertEqual(response.status_code, 302)

        # Step 4: Verify all photos were uploaded
        batch_series = PhotoSeries.objects.filter(
            patient=self.patient, description__icontains="Batch upload test"
        ).first()
        self.assertIsNotNone(batch_series)
        self.assertEqual(batch_series.get_photo_count(), 8)

        # Step 5: Verify reasonable upload time (should be under 10 seconds)
        self.assertLess(
            upload_time, 10.0, f"Batch upload took {upload_time:.2f}s, should be < 10s"
        )

        # Step 6: Verify gallery loads efficiently
        detail_url = reverse(
            "mediafiles:photoseries_detail", kwargs={"pk": batch_series.pk}
        )
        start_time = time.time()
        response = self.client.get(detail_url)
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(
            load_time, 3.0, f"Gallery loading took {load_time:.2f}s, should be < 3s"
        )

    def test_scenario_ps6_security_validation_comprehensive(self):
        """
        Scenario PS6: Security - Comprehensive security validation for PhotoSeries

        User Story: As a system administrator, I need to ensure PhotoSeries uploads
        maintain the same security standards as individual photos, with additional
        validation for batch operations.
        """
        upload_url = reverse(
            "mediafiles:photoseries_create", kwargs={"patient_id": self.patient.pk}
        )

        # Test 1: An unknown/expired upload id rejects the entire batch
        form_data = {
            "description": "Security test - mixed files",
            "event_datetime": past_datetime_str(),
            "caption": "Security validation test",
            "upload_ids": ",".join([create_temp_upload("valid1.jpg"), "z" * 22]),
        }
        response = self.client.post(upload_url, form_data)
        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_ids", response.context["form"].errors)

        # Verify no PhotoSeries was created
        self.assertFalse(
            PhotoSeries.objects.filter(
                patient=self.patient, description="Security test - mixed files"
            ).exists()
        )

        # Test 2: Valid files should work
        form_data["upload_ids"] = ",".join(
            [create_temp_upload("secure1.jpg"), create_temp_upload("secure2.jpg")]
        )
        form_data["description"] = "Security test - valid files"
        response = self.client.post(upload_url, form_data)
        self.assertEqual(response.status_code, 302)

        # Verify PhotoSeries was created
        secure_series = PhotoSeries.objects.filter(
            patient=self.patient, description="Security test - valid files"
        ).first()
        self.assertIsNotNone(secure_series)
        self.assertEqual(secure_series.get_photo_count(), 2)

        # Test 3: Verify secure file storage (UUID paths, no original names)
        for series_file in secure_series.get_ordered_photos():
            file_path = (
                Path(settings.MEDIA_ROOT)
                / f"photo_series/{secure_series.created_at.strftime('%Y/%m')}/originals"
                / f"{series_file.file_id}.jpg"
            )
            self.assertTrue(file_path.exists())
            self.assertNotIn("secure1", file_path.name)
            self.assertNotIn("secure2", file_path.name)
            # UUID-based naming (36 chars without extension)
            name_without_ext = file_path.name.rsplit(".", 1)[0]
            self.assertEqual(len(name_without_ext), 36)
