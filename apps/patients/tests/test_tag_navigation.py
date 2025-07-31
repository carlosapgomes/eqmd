from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Patient, AllowedTag, Tag

User = get_user_model()


class PatientTagNavigationTests(TestCase):
    """Tests for navigation flow from forms to detail page for tag management"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        # Add required permissions
        from django.contrib.auth.models import Permission
        add_perm = Permission.objects.get(codename='add_patient')
        change_perm = Permission.objects.get(codename='change_patient')
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(add_perm, change_perm, view_perm)
        
        cls.allowed_tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#007bff',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_patient_create_form_redirects_to_detail_page(self):
        """Test that patient creation redirects to detail page where tags can be managed"""
        create_url = reverse('patients:patient_create')
        
        response = self.client.post(create_url, data={
            'name': 'John Doe',
            'birthday': '1990-01-01',
            'status': Patient.Status.OUTPATIENT,
            'gender': Patient.GenderChoices.MALE,
        })
        
        # Should redirect to detail page after creation
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/patients/'))
        
        # Follow redirect to detail page
        detail_response = self.client.get(response.url)
        self.assertEqual(detail_response.status_code, 200)
        
        # Verify detail page contains tag management section
        self.assertContains(detail_response, 'Gerenciamento de Tags')
        self.assertContains(detail_response, 'Adicionar Tag')
        
        # Verify patient was created successfully
        patient = Patient.objects.get(name='John Doe')
        self.assertEqual(patient.tags.count(), 0)

    def test_patient_update_form_redirects_to_detail_page(self):
        """Test that patient update redirects to detail page where tags can be managed"""
        # Create a patient first
        patient = Patient.objects.create(
            name='Jane Doe',
            birthday='1985-05-15',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        update_url = reverse('patients:patient_update', kwargs={'pk': patient.pk})
        
        response = self.client.post(update_url, data={
            'name': 'Jane Smith',  # Updated name
            'birthday': '1985-05-15',
            'status': Patient.Status.INPATIENT,
            'gender': Patient.GenderChoices.FEMALE,
        })
        
        # Should redirect to detail page after update
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/patients/'))
        
        # Follow redirect to detail page
        detail_response = self.client.get(response.url)
        self.assertEqual(detail_response.status_code, 200)
        
        # Verify detail page contains tag management section
        self.assertContains(detail_response, 'Gerenciamento de Tags')
        self.assertContains(detail_response, 'Adicionar Tag')
        
        # Verify patient was updated successfully
        patient.refresh_from_db()
        self.assertEqual(patient.name, 'Jane Smith')

    def test_tag_management_links_accessible_from_detail_page(self):
        """Test that tag management links are properly accessible from detail page"""
        # Create a patient
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tag management section is present
        self.assertContains(response, 'Gerenciamento de Tags')
        self.assertContains(response, 'Adicionar Tag')
        
        # Verify JavaScript for tag management is present
        self.assertContains(response, 'loadAvailableTags')
        self.assertContains(response, 'addTagToPatient')
        self.assertContains(response, 'removeTagFromPatient')

    def test_detail_page_shows_existing_tags(self):
        """Test that detail page shows existing tags with proper styling"""
        # Create a patient
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag to the patient
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            notes='Test tag for navigation',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tag is displayed with proper styling
        self.assertContains(response, 'Test Tag')
        self.assertContains(response, '#007bff')  # Tag color
        self.assertContains(response, 'bi-tag-fill')  # Tag icon
        self.assertContains(response, 'remove-tag-btn')  # Remove button

    def test_detail_page_tag_management_permissions(self):
        """Test that tag management respects user permissions"""
        # Create a user without change_patient permission
        limited_user = User.objects.create_user(
            username='limiteduser',
            email='limited@example.com',
            password='testpassword'
        )
        # Only add view permission
        from django.contrib.auth.models import Permission
        view_perm = Permission.objects.get(codename='view_patient')
        limited_user.user_permissions.add(view_perm)
        
        # Create a patient
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Login with limited user
        self.client.force_login(limited_user)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tag management section is present
        self.assertContains(response, 'Gerenciamento de Tags')

    def test_breadcrumb_navigation_includes_tag_management(self):
        """Test that breadcrumb navigation properly includes tag management context"""
        # Create a patient
        patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify breadcrumb navigation is present
        self.assertContains(response, 'breadcrumb')
        self.assertContains(response, 'Pacientes')
        self.assertContains(response, patient.name)

    def test_form_submission_success_message_leads_to_tag_management(self):
        """Test that success messages guide users to tag management"""
        create_url = reverse('patients:patient_create')
        
        response = self.client.post(create_url, data={
            'name': 'New Patient',
            'birthday': '1995-03-10',
            'status': Patient.Status.OUTPATIENT,
            'gender': Patient.GenderChoices.OTHER,
        }, follow=True)
        
        # Should be on detail page now
        self.assertEqual(response.status_code, 200)
        
        # Verify tag management section is prominent
        self.assertContains(response, 'Gerenciamento de Tags')
        self.assertContains(response, 'Adicionar Tag')
        self.assertContains(response, 'Nenhuma tag atribuída')

    def test_cancel_form_returns_to_list_with_tag_management_hint(self):
        """Test that canceling forms returns to list with tag management hints"""
        create_url = reverse('patients:patient_create')
        
        # Just visit the create form
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify there's a cancel/back to list link
        self.assertContains(response, 'Cancelar')
        
        # Go to list page
        list_url = reverse('patients:patient_list')
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, 200)
        
        # Verify list page exists and works
        self.assertContains(list_response, 'Pacientes')

    def test_mobile_responsive_tag_management_navigation(self):
        """Test that tag management navigation works on mobile devices"""
        # Create a patient
        patient = Patient.objects.create(
            name='Mobile Test Patient',
            birthday='1992-07-20',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test with mobile user agent
        mobile_user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
        
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url, HTTP_USER_AGENT=mobile_user_agent)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tag management is mobile-responsive
        self.assertContains(response, 'Gerenciamento de Tags')
        self.assertContains(response, 'btn-sm')  # Small buttons for mobile
        self.assertContains(response, 'modal-lg')  # Large modal for better mobile experience

    def test_accessibility_of_tag_management_navigation(self):
        """Test that tag management navigation is accessible"""
        # Create a patient
        patient = Patient.objects.create(
            name='Accessibility Test Patient',
            birthday='1988-11-30',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify basic accessibility features
        self.assertContains(response, 'Gerenciamento de Tags')
        self.assertContains(response, 'Adicionar Tag')

    def test_tag_management_workflow_after_patient_creation(self):
        """Test complete workflow: create patient -> manage tags -> verify results"""
        # 1. Create patient
        create_url = reverse('patients:patient_create')
        response = self.client.post(create_url, data={
            'name': 'Workflow Test Patient',
            'birthday': '1993-04-15',
            'status': Patient.Status.OUTPATIENT,
            'gender': Patient.GenderChoices.NOT_INFORMED,
        }, follow=True)
        
        # 2. Verify on detail page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Workflow Test Patient')
        
        # 3. Extract patient ID from URL
        patient = Patient.objects.get(name='Workflow Test Patient')
        
        # 4. Add tag via API (simulating JavaScript)
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Added during workflow test'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # 5. Verify tag was added
        self.assertEqual(patient.tags.count(), 1)
        tag = patient.tags.first()
        self.assertEqual(tag.allowed_tag.name, 'Test Tag')
        
        # 6. Go back to detail page and verify tag display
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Test Tag')

    def test_error_handling_during_navigation_workflow(self):
        """Test error handling when navigation workflow encounters issues"""
        # Try to access non-existent patient detail page
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        detail_url = reverse('patients:patient_detail', kwargs={'pk': fake_uuid})
        response = self.client.get(detail_url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
        
        # Try to update non-existent patient
        update_url = reverse('patients:patient_update', kwargs={'pk': fake_uuid})
        response = self.client.get(update_url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_performance_of_navigation_with_many_tags(self):
        """Test that navigation performance is good with many tags"""
        # Create multiple allowed tags
        allowed_tags = []
        for i in range(20):
            tag = AllowedTag.objects.create(
                name=f'Tag {i+1}',
                color=f'#{i:02x}{i:02x}{i:02x}',
                created_by=self.user,
                updated_by=self.user
            )
            allowed_tags.append(tag)
        
        # Create a patient
        patient = Patient.objects.create(
            name='Performance Test Patient',
            birthday='1991-09-25',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add multiple tags to patient
        for i, allowed_tag in enumerate(allowed_tags[:10]):  # Add first 10 tags
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Performance test tag {i+1}',
                created_by=self.user,
                updated_by=self.user
            )
            patient.tags.add(tag)
        
        # Test detail page loading performance
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        
        import time
        start_time = time.time()
        response = self.client.get(detail_url)
        end_time = time.time()
        
        # Should load quickly (under 2 seconds)
        load_time = end_time - start_time
        self.assertLess(load_time, 2.0, f"Detail page loaded in {load_time:.2f}s, expected < 2s")
        
        # Verify all tags are displayed
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Performance Test Patient')
        
        # Should show tag count
        self.assertContains(response, 'Total de tags: <span id="tag-count">10</span>')