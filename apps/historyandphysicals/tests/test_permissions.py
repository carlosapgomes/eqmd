from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from apps.core.permissions import can_access_patient, can_edit_event, can_delete_event
from ..models import HistoryAndPhysical

User = get_user_model()


class HistoryAndPhysicalPermissionsTest(TestCase):
    """Test permissions for HistoryAndPhysical operations."""

    def setUp(self):
        """Set up test data."""
        # Create hospitals
        self.hospital1 = Hospital.objects.create(
            name='Hospital 1',
            address='123 Test St'
        )
        self.hospital2 = Hospital.objects.create(
            name='Hospital 2',
            address='456 Other St'
        )
        
        # Create users with different profession types
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=User.NURSE
        )
        
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            profession_type=User.STUDENT
        )
        
        # Assign users to hospitals
        self.doctor.hospitals.add(self.hospital1)
        self.nurse.hospitals.add(self.hospital1)
        self.student.hospitals.add(self.hospital1, self.hospital2)
        
        # Create patients
        self.inpatient = Patient.objects.create(
            name='Inpatient Test',
            birthday='1990-01-01',
            status=Patient.INPATIENT,
            current_hospital=self.hospital1,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.outpatient = Patient.objects.create(
            name='Outpatient Test',
            birthday='1985-01-01',
            status=Patient.OUTPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create history and physicals
        self.recent_historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description='Recent History and Physical',
            content='Recent content.',
            patient=self.inpatient,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.old_historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now() - timezone.timedelta(hours=25),  # More than 24 hours old
            description='Old History and Physical',
            content='Old content.',
            patient=self.inpatient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

    def test_doctor_can_access_all_patients(self):
        """Test that doctors can access all patients in their hospitals."""
        # Doctor should be able to access inpatient
        self.assertTrue(can_access_patient(self.doctor, self.inpatient))
        
        # Doctor should be able to access outpatient
        self.assertTrue(can_access_patient(self.doctor, self.outpatient))

    def test_nurse_can_access_hospital_patients(self):
        """Test that nurses can access patients in their hospitals."""
        # Nurse should be able to access inpatient in same hospital
        self.assertTrue(can_access_patient(self.nurse, self.inpatient))
        
        # Nurse should be able to access outpatient
        self.assertTrue(can_access_patient(self.nurse, self.outpatient))

    def test_student_can_only_access_outpatients(self):
        """Test that students can only access outpatients."""
        # Student should NOT be able to access inpatient
        self.assertFalse(can_access_patient(self.student, self.inpatient))
        
        # Student should be able to access outpatient
        self.assertTrue(can_access_patient(self.student, self.outpatient))

    def test_can_edit_recent_historyandphysical(self):
        """Test that users can edit recent history and physicals (within 24 hours)."""
        # Creator should be able to edit recent history and physical
        self.assertTrue(can_edit_event(self.doctor, self.recent_historyandphysical))
        
        # Other doctor should also be able to edit recent history and physical
        other_doctor = User.objects.create_user(
            username='otherdoc',
            email='otherdoc@test.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        other_doctor.hospitals.add(self.hospital1)
        self.assertTrue(can_edit_event(other_doctor, self.recent_historyandphysical))

    def test_cannot_edit_old_historyandphysical(self):
        """Test that users cannot edit old history and physicals (older than 24 hours)."""
        # Even creator should not be able to edit old history and physical
        self.assertFalse(can_edit_event(self.doctor, self.old_historyandphysical))

    def test_can_delete_recent_historyandphysical(self):
        """Test that users can delete recent history and physicals."""
        # Creator should be able to delete recent history and physical
        self.assertTrue(can_delete_event(self.doctor, self.recent_historyandphysical))

    def test_cannot_delete_old_historyandphysical(self):
        """Test that users cannot delete old history and physicals."""
        # Even creator should not be able to delete old history and physical
        self.assertFalse(can_delete_event(self.doctor, self.old_historyandphysical))

    def test_view_permissions_in_detail_view(self):
        """Test that detail view properly checks permissions."""
        client = Client()
        
        # Login as doctor
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:historyandphysical_detail',
                     kwargs={'pk': self.recent_historyandphysical.pk})
        response = client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Login as student and try to access inpatient's history and physical
        client.login(username='student', password='testpass123')
        
        response = client.get(url)
        # Should be denied access
        self.assertIn(response.status_code, [403, 302])

    def test_create_permissions(self):
        """Test create permissions for history and physicals."""
        client = Client()
        
        # Doctor should be able to create
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:patient_historyandphysical_create',
                     kwargs={'patient_pk': self.inpatient.pk})
        
        form_data = {
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'content': 'New history and physical content with enough characters.'
        }
        
        response = client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Successful redirect
        
        # Student should not be able to create for inpatient
        client.login(username='student', password='testpass123')
        
        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_update_permissions(self):
        """Test update permissions for history and physicals."""
        client = Client()
        
        # Doctor should be able to update recent history and physical
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:historyandphysical_update',
                     kwargs={'pk': self.recent_historyandphysical.pk})
        
        form_data = {
            'event_datetime': self.recent_historyandphysical.event_datetime.strftime('%Y-%m-%dT%H:%M'),
            'content': 'Updated history and physical content with enough characters.'
        }
        
        response = client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Successful redirect
        
        # Should not be able to update old history and physical
        url = reverse('apps.historyandphysicals:historyandphysical_update',
                     kwargs={'pk': self.old_historyandphysical.pk})
        
        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_delete_permissions(self):
        """Test delete permissions for history and physicals."""
        client = Client()
        
        # Doctor should be able to delete recent history and physical
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:historyandphysical_delete',
                     kwargs={'pk': self.recent_historyandphysical.pk})
        
        response = client.get(url)
        self.assertEqual(response.status_code, 200)  # Can access delete page
        
        # Should not be able to delete old history and physical
        url = reverse('apps.historyandphysicals:historyandphysical_delete',
                     kwargs={'pk': self.old_historyandphysical.pk})
        
        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_duplicate_permissions(self):
        """Test duplicate permissions for history and physicals."""
        client = Client()
        
        # Doctor should be able to duplicate history and physical
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:historyandphysical_duplicate',
                     kwargs={'pk': self.recent_historyandphysical.pk})
        
        response = client.get(url)
        self.assertEqual(response.status_code, 200)  # Can access duplicate page
        
        # Student should not be able to duplicate inpatient's history and physical
        client.login(username='student', password='testpass123')
        
        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_print_permissions(self):
        """Test print permissions for history and physicals."""
        client = Client()
        
        # Doctor should be able to print
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:historyandphysical_print',
                     kwargs={'pk': self.recent_historyandphysical.pk})
        
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Student should not be able to print inpatient's history and physical
        client.login(username='student', password='testpass123')
        
        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_export_permissions(self):
        """Test export permissions for patient history and physicals."""
        client = Client()
        
        # Doctor should be able to export
        client.login(username='doctor', password='testpass123')
        
        url = reverse('apps.historyandphysicals:patient_historyandphysical_export',
                     kwargs={'patient_pk': self.inpatient.pk})
        
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Student should not be able to export inpatient's history and physicals
        client.login(username='student', password='testpass123')
        
        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])