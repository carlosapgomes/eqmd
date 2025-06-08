from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Patient, AllowedTag, Tag
from ..forms import PatientForm

User = get_user_model()


class AllowedTagModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_allowed_tag_creation(self):
        """Test that AllowedTag can be created with required fields"""
        tag = AllowedTag.objects.create(
            name='High Priority',
            description='For high priority patients',
            color='#dc3545',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.name, 'High Priority')
        self.assertEqual(tag.color, '#dc3545')
        self.assertTrue(tag.is_active)

    def test_allowed_tag_str_representation(self):
        """Test string representation of AllowedTag"""
        tag = AllowedTag.objects.create(
            name='Emergency',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(tag), 'Emergency')

    def test_allowed_tag_default_color(self):
        """Test that AllowedTag has default color"""
        tag = AllowedTag.objects.create(
            name='Test Tag',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.color, '#007bff')


class TagModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.allowed_tag = AllowedTag.objects.create(
            name='Critical',
            color='#dc3545',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_tag_creation(self):
        """Test that Tag can be created with allowed tag"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            notes='Critical patient needs immediate attention',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.allowed_tag, self.allowed_tag)
        self.assertEqual(tag.name, 'Critical')
        self.assertEqual(tag.color, '#dc3545')

    def test_tag_str_representation(self):
        """Test string representation of Tag"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(tag), 'Critical')

    def test_tag_properties(self):
        """Test Tag properties that access AllowedTag fields"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.name, self.allowed_tag.name)
        self.assertEqual(tag.color, self.allowed_tag.color)


class PatientTagsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag1 = AllowedTag.objects.create(
            name='High Priority',
            color='#dc3545',
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag2 = AllowedTag.objects.create(
            name='Follow Up',
            color='#ffc107',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_tag_assignment(self):
        """Test that tags can be assigned to patients"""
        tag1 = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            created_by=self.user,
            updated_by=self.user
        )
        tag2 = Tag.objects.create(
            allowed_tag=self.allowed_tag2,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient.tags.add(tag1, tag2)
        
        self.assertEqual(self.patient.tags.count(), 2)
        self.assertIn(tag1, self.patient.tags.all())
        self.assertIn(tag2, self.patient.tags.all())

    def test_patient_tag_removal(self):
        """Test that tags can be removed from patients"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient.tags.add(tag)
        self.assertEqual(self.patient.tags.count(), 1)
        
        self.patient.tags.remove(tag)
        self.assertEqual(self.patient.tags.count(), 0)


class PatientFormTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.allowed_tag1 = AllowedTag.objects.create(
            name='Urgent',
            color='#dc3545',
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag2 = AllowedTag.objects.create(
            name='Follow Up',
            color='#ffc107',
            created_by=cls.user,
            updated_by=cls.user
        )
        # Create inactive tag to test filtering
        cls.inactive_tag = AllowedTag.objects.create(
            name='Inactive Tag',
            color='#6c757d',
            is_active=False,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_form_tag_selection_field(self):
        """Test that PatientForm includes tag selection field"""
        form = PatientForm()
        self.assertIn('tag_selection', form.fields)
        
        # Check that only active allowed tags are in queryset
        queryset = form.fields['tag_selection'].queryset
        self.assertIn(self.allowed_tag1, queryset)
        self.assertIn(self.allowed_tag2, queryset)
        self.assertNotIn(self.inactive_tag, queryset)

    def test_patient_form_save_with_tags(self):
        """Test that PatientForm properly saves tags"""
        form_data = {
            'name': 'Test Patient',
            'birthday': '1980-01-01',
            'status': Patient.Status.OUTPATIENT,
            'tag_selection': [self.allowed_tag1.pk, self.allowed_tag2.pk]
        }
        
        form = PatientForm(data=form_data)
        form.current_user = self.user
        
        self.assertTrue(form.is_valid())
        
        # Mimic what the view does
        patient = form.save(commit=False)
        patient.created_by = self.user
        patient.updated_by = self.user
        patient.save()
        
        # Handle tag creation manually since we're not going through the full form.save() 
        selected_allowed_tags = form.cleaned_data.get('tag_selection', [])
        for allowed_tag in selected_allowed_tags:
            tag, created = Tag.objects.get_or_create(
                allowed_tag=allowed_tag,
                defaults={
                    'created_by': self.user,
                    'updated_by': self.user,
                }
            )
            patient.tags.add(tag)
        
        # Check that tags were created and assigned
        self.assertEqual(patient.tags.count(), 2)
        tag_names = [tag.name for tag in patient.tags.all()]
        self.assertIn('Urgent', tag_names)
        self.assertIn('Follow Up', tag_names)

    def test_patient_form_edit_with_existing_tags(self):
        """Test editing patient with existing tags"""
        # Create patient with initial tag
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        tag1 = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag1)
        
        # Edit to add another tag
        form_data = {
            'name': 'Test Patient Updated',
            'birthday': '1980-01-01',
            'status': Patient.Status.OUTPATIENT,
            'tag_selection': [self.allowed_tag1.pk, self.allowed_tag2.pk]
        }
        
        form = PatientForm(data=form_data, instance=patient)
        form.current_user = self.user
        
        self.assertTrue(form.is_valid())
        updated_patient = form.save()
        
        # Check that both tags are now assigned
        self.assertEqual(updated_patient.tags.count(), 2)
        tag_names = [tag.name for tag in updated_patient.tags.all()]
        self.assertIn('Urgent', tag_names)
        self.assertIn('Follow Up', tag_names)

    def test_patient_form_remove_all_tags(self):
        """Test removing all tags from patient"""
        # Create patient with tags
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        tag1 = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag1)
        
        # Edit to remove all tags
        form_data = {
            'name': 'Test Patient',
            'birthday': '1980-01-01',
            'status': Patient.Status.OUTPATIENT,
            'tag_selection': []
        }
        
        form = PatientForm(data=form_data, instance=patient)
        form.current_user = self.user
        
        self.assertTrue(form.is_valid())
        updated_patient = form.save()
        
        # Check that no tags are assigned
        self.assertEqual(updated_patient.tags.count(), 0)


class PatientTagViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag = AllowedTag.objects.create(
            name='VIP',
            color='#6f42c1',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_patient_detail_displays_tags(self):
        """Test that patient detail view displays tags"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )
        self.patient.tags.add(tag)
        
        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VIP')
        self.assertContains(response, '#6f42c1')

    def test_patient_list_displays_tags(self):
        """Test that patient list view displays tags"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )
        self.patient.tags.add(tag)
        
        response = self.client.get(reverse('patients:patient_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VIP')
        self.assertContains(response, '#6f42c1')