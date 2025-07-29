from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from ..models import Patient

User = get_user_model()


class PatientViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Add permissions
        content_type = ContentType.objects.get_for_model(Patient)
        permissions = Permission.objects.filter(content_type=content_type)
        cls.user.user_permissions.add(*permissions)

        # Create test data
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')

    def test_patient_list_view(self):
        response = self.client.get(reverse('patients:patient_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Patient')
        self.assertTemplateUsed(response, 'patients/patient_list.html')

    def test_patient_detail_view(self):
        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Patient')
        self.assertTemplateUsed(response, 'patients/patient_detail.html')

    def test_patient_create_view(self):
        response = self.client.get(reverse('patients:patient_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_form.html')

        # Test form submission
        response = self.client.post(reverse('patients:patient_create'), {
            'name': 'New Patient',
            'birthday': '1990-01-01',
            'gender': Patient.GenderChoices.FEMALE,
            'status': Patient.Status.OUTPATIENT,
        })
        self.assertEqual(Patient.objects.filter(name='New Patient').count(), 1)
        
        # Verify gender was saved correctly
        new_patient = Patient.objects.get(name='New Patient')
        self.assertEqual(new_patient.gender, Patient.GenderChoices.FEMALE)

    def test_patient_update_view(self):
        response = self.client.get(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_form.html')

        # Test form submission
        response = self.client.post(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk}),
            {
                'name': 'Updated Patient',
                'birthday': '1980-01-01',
                'gender': Patient.GenderChoices.MALE,
                'status': Patient.Status.OUTPATIENT,
            }
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, 'Updated Patient')
        self.assertEqual(self.patient.gender, Patient.GenderChoices.MALE)

    def test_patient_delete_view(self):
        response = self.client.get(
            reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_confirm_delete.html')

        # Test deletion
        response = self.client.post(
            reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(Patient.objects.filter(pk=self.patient.pk).count(), 0)

    def test_permission_required(self):
        # Create a user without permissions
        user_no_perms = User.objects.create_user(
            username='noperms',
            email='noperms@example.com',
            password='testpassword'
        )

        # Log in as the user without permissions
        self.client.logout()
        self.client.login(username='noperms', password='testpassword')

        # Test create view
        response = self.client.get(reverse('patients:patient_create'))
        self.assertEqual(response.status_code, 403)  # Permission denied

        # Test update view
        response = self.client.get(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 403)  # Permission denied

        # Test delete view
        response = self.client.get(
            reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 403)  # Permission denied

    def test_patient_create_with_default_gender(self):
        """Test patient creation without specifying gender uses default"""
        response = self.client.post(reverse('patients:patient_create'), {
            'name': 'Default Gender Patient',
            'birthday': '1990-01-01',
            'status': Patient.Status.OUTPATIENT,
        })
        self.assertEqual(Patient.objects.filter(name='Default Gender Patient').count(), 1)
        
        # Verify default gender was applied
        patient = Patient.objects.get(name='Default Gender Patient')
        self.assertEqual(patient.gender, Patient.GenderChoices.NOT_INFORMED)

    def test_patient_create_with_all_gender_choices(self):
        """Test patient creation with all valid gender choices"""
        gender_choices = [
            Patient.GenderChoices.MALE,
            Patient.GenderChoices.FEMALE,
            Patient.GenderChoices.OTHER,
            Patient.GenderChoices.NOT_INFORMED
        ]
        
        for i, gender in enumerate(gender_choices):
            patient_name = f'Gender Test Patient {i}'
            response = self.client.post(reverse('patients:patient_create'), {
                'name': patient_name,
                'birthday': '1990-01-01',
                'gender': gender,
                'status': Patient.Status.OUTPATIENT,
            })
            
            # Check patient was created successfully
            self.assertEqual(Patient.objects.filter(name=patient_name).count(), 1)
            
            # Verify gender was saved correctly
            patient = Patient.objects.get(name=patient_name)
            self.assertEqual(patient.gender, gender)

    def test_patient_update_gender_change(self):
        """Test updating patient gender"""
        # Start with default gender
        self.assertEqual(self.patient.gender, Patient.GenderChoices.NOT_INFORMED)
        
        # Update to male
        response = self.client.post(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk}),
            {
                'name': self.patient.name,
                'birthday': self.patient.birthday,
                'gender': Patient.GenderChoices.MALE,
                'status': self.patient.status,
            }
        )
        
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.gender, Patient.GenderChoices.MALE)
        
        # Update to female
        response = self.client.post(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk}),
            {
                'name': self.patient.name,
                'birthday': self.patient.birthday,
                'gender': Patient.GenderChoices.FEMALE,
                'status': self.patient.status,
            }
        )
        
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.gender, Patient.GenderChoices.FEMALE)

    def test_patient_detail_view_displays_gender(self):
        """Test that patient detail view displays gender information"""
        # Update patient to have a specific gender
        self.patient.gender = Patient.GenderChoices.MALE
        self.patient.save()
        
        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that gender information is in the response
        self.assertContains(response, 'Masculino')  # Portuguese label for male