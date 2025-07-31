from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, AllowedTag, Tag

User = get_user_model()

class TagArchitectureRefactorTests(TestCase):
    """Test the new tag architecture allows multiple patients to share tag types"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        # Create two patients
        self.patient1 = Patient.objects.create(
            name='Patient One',
            birthday='1990-01-01',
            gender='M',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient2 = Patient.objects.create(
            name='Patient Two',
            birthday='1985-05-15',
            gender='F',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create allowed tags
        self.high_priority_tag = AllowedTag.objects.create(
            name='High Priority',
            color='red',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.diabetic_tag = AllowedTag.objects.create(
            name='Diabetic',
            color='blue',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )

    def test_multiple_patients_can_share_same_tag_type(self):
        """Test that multiple patients can have the same AllowedTag assigned"""
        
        # Assign "High Priority" tag to both patients
        tag1 = Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            patient=self.patient1,
            notes="Patient 1 needs immediate attention",
            created_by=self.user,
            updated_by=self.user
        )
        
        tag2 = Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            patient=self.patient2,
            notes="Patient 2 also needs priority care",
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify both tags were created successfully
        self.assertIsNotNone(tag1.id)
        self.assertIsNotNone(tag2.id)
        self.assertNotEqual(tag1.id, tag2.id)
        
        # Verify both tags reference the same AllowedTag
        self.assertEqual(tag1.allowed_tag, self.high_priority_tag)
        self.assertEqual(tag2.allowed_tag, self.high_priority_tag)
        
        # Verify each tag belongs to the correct patient
        self.assertEqual(tag1.patient, self.patient1)
        self.assertEqual(tag2.patient, self.patient2)
        
        # Verify patients can access their tags through reverse relationship
        patient1_tags = self.patient1.patient_tags.all()
        patient2_tags = self.patient2.patient_tags.all()
        
        self.assertEqual(patient1_tags.count(), 1)
        self.assertEqual(patient2_tags.count(), 1)
        
        self.assertIn(tag1, patient1_tags)
        self.assertIn(tag2, patient2_tags)

    def test_same_patient_cannot_have_duplicate_tag_types(self):
        """Test that the same patient cannot have the same AllowedTag assigned twice"""
        from django.db import IntegrityError
        
        # Assign "Diabetic" tag to patient1
        tag1 = Tag.objects.create(
            allowed_tag=self.diabetic_tag,
            patient=self.patient1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify the first tag was created
        self.assertIsNotNone(tag1.id)
        
        # Try to assign the same AllowedTag to the same patient again
        with self.assertRaises(IntegrityError):  # Should raise IntegrityError due to unique constraint
            Tag.objects.create(
                allowed_tag=self.diabetic_tag,
                patient=self.patient1,
                created_by=self.user,
                updated_by=self.user
            )

    def test_complex_multi_patient_tag_scenario(self):
        """Test complex scenario with multiple patients and multiple shared tags"""
        
        # Create third patient
        patient3 = Patient.objects.create(
            name='Patient Three',
            birthday='1995-12-20',
            gender='O',
            status=Patient.Status.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Assign "High Priority" to all three patients
        for i, patient in enumerate([self.patient1, self.patient2, patient3], 1):
            Tag.objects.create(
                allowed_tag=self.high_priority_tag,
                patient=patient,
                notes=f"High priority notes for patient {i}",
                created_by=self.user,
                updated_by=self.user
            )
        
        # Assign "Diabetic" to patient1 and patient3 only
        Tag.objects.create(
            allowed_tag=self.diabetic_tag,
            patient=self.patient1,
            notes="Type 2 diabetes",
            created_by=self.user,
            updated_by=self.user
        )
        
        Tag.objects.create(
            allowed_tag=self.diabetic_tag,
            patient=patient3,
            notes="Type 1 diabetes",
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify tag counts
        self.assertEqual(self.patient1.patient_tags.count(), 2)  # High Priority + Diabetic
        self.assertEqual(self.patient2.patient_tags.count(), 1)  # High Priority only
        self.assertEqual(patient3.patient_tags.count(), 2)       # High Priority + Diabetic
        
        # Verify AllowedTag instances are shared
        high_priority_assignments = Tag.objects.filter(allowed_tag=self.high_priority_tag)
        diabetic_assignments = Tag.objects.filter(allowed_tag=self.diabetic_tag)
        
        self.assertEqual(high_priority_assignments.count(), 3)  # 3 patients
        self.assertEqual(diabetic_assignments.count(), 2)       # 2 patients
        
        # Verify tag names are accessible
        patient1_tag_names = [tag.allowed_tag.name for tag in self.patient1.patient_tags.all()]
        self.assertIn('High Priority', patient1_tag_names)
        self.assertIn('Diabetic', patient1_tag_names)
        
        patient2_tag_names = [tag.allowed_tag.name for tag in self.patient2.patient_tags.all()]
        self.assertIn('High Priority', patient2_tag_names)
        self.assertNotIn('Diabetic', patient2_tag_names)

    def test_tag_deletion_affects_only_specific_patient(self):
        """Test that deleting a tag from one patient doesn't affect other patients"""
        
        # Assign same tag to both patients
        tag1 = Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            patient=self.patient1,
            created_by=self.user,
            updated_by=self.user
        )
        
        tag2 = Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            patient=self.patient2,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify both patients have the tag
        self.assertEqual(self.patient1.patient_tags.count(), 1)
        self.assertEqual(self.patient2.patient_tags.count(), 1)
        
        # Delete tag from patient1
        tag1.delete()
        
        # Verify patient1 no longer has the tag, but patient2 still does
        self.assertEqual(self.patient1.patient_tags.count(), 0)
        self.assertEqual(self.patient2.patient_tags.count(), 1)
        
        # Verify the AllowedTag still exists
        self.assertTrue(AllowedTag.objects.filter(id=self.high_priority_tag.id).exists())
        
        # Verify patient2's tag is still functional
        remaining_tag = self.patient2.patient_tags.first()
        self.assertEqual(remaining_tag.allowed_tag, self.high_priority_tag)

    def test_allowed_tag_deletion_cascades_properly(self):
        """Test that deleting an AllowedTag cascades to all Tag instances"""
        
        # Assign same AllowedTag to both patients
        Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            patient=self.patient1,
            created_by=self.user,
            updated_by=self.user
        )
        
        Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            patient=self.patient2,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify both patients have tags
        self.assertEqual(self.patient1.patient_tags.count(), 1)
        self.assertEqual(self.patient2.patient_tags.count(), 1)
        
        # Delete the AllowedTag
        self.high_priority_tag.delete()
        
        # Verify all Tag instances are deleted due to CASCADE
        self.assertEqual(self.patient1.patient_tags.count(), 0)
        self.assertEqual(self.patient2.patient_tags.count(), 0)
        self.assertEqual(Tag.objects.filter(allowed_tag=self.high_priority_tag.id).count(), 0)