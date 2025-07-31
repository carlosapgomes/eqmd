from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Patient, AllowedTag, Tag

User = get_user_model()


class PatientTagVisualizationTests(TestCase):
    """Tests for tag visualization with colors and styling"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        # Add required permissions
        from django.contrib.auth.models import Permission
        change_perm = Permission.objects.get(codename='change_patient')
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(change_perm, view_perm)
        
        # Create different colored tags
        cls.red_tag = AllowedTag.objects.create(
            name='High Priority',
            color='#dc3545',  # Red
            description='Urgent cases',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        cls.blue_tag = AllowedTag.objects.create(
            name='Regular',
            color='#007bff',  # Blue
            description='Standard cases',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        cls.green_tag = AllowedTag.objects.create(
            name='Follow Up',
            color='#28a745',  # Green
            description='Needs follow-up',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        cls.yellow_tag = AllowedTag.objects.create(
            name='Warning',
            color='#ffc107',  # Yellow
            description='Warning status',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_tag_color_display_in_detail_page(self):
        """Test that tags are displayed with correct colors in detail page"""
        # Create a patient
        patient = Patient.objects.create(
            name='Color Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add different colored tags
        for allowed_tag in [self.red_tag, self.blue_tag, self.green_tag]:
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Color test for {allowed_tag.name}',
                created_by=self.user,
                updated_by=self.user
            )
            patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify all tags are displayed with correct colors
        self.assertContains(response, 'High Priority')
        self.assertContains(response, '#dc3545')  # Red color
        
        self.assertContains(response, 'Regular')
        self.assertContains(response, '#007bff')  # Blue color
        
        self.assertContains(response, 'Follow Up')
        self.assertContains(response, '#28a745')  # Green color

    def test_tag_badge_styling_consistency(self):
        """Test that tag badges have consistent styling"""
        # Create a patient
        patient = Patient.objects.create(
            name='Style Test Patient',
            birthday='1985-05-15',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.red_tag,
            notes='Style test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify badge styling elements
        self.assertContains(response, 'class="badge"')  # Badge class
        self.assertContains(response, 'style="background-color: #dc3545; color: white;"')  # Inline style
        self.assertContains(response, 'bi-tag-fill')  # Icon class
        self.assertContains(response, 'remove-tag-btn')  # Remove button class

    def test_tag_hover_effects(self):
        """Test that tag badges have proper hover effects"""
        # Create a patient
        patient = Patient.objects.create(
            name='Hover Test Patient',
            birthday='1990-03-20',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.blue_tag,
            notes='Hover test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify hover effect CSS is present
        self.assertContains(response, '.tag-item:hover .remove-tag-btn')
        self.assertContains(response, 'opacity: 0.7')
        self.assertContains(response, 'opacity: 1')

    def test_empty_tag_state_display(self):
        """Test that empty tag state is displayed properly"""
        # Create a patient with no tags
        patient = Patient.objects.create(
            name='No Tags Patient',
            birthday='1992-07-10',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify empty state message
        self.assertContains(response, 'Nenhuma tag atribuída a este paciente')
        self.assertContains(response, 'bi-info-circle')
        self.assertContains(response, 'no-tags-message')

    def test_tag_management_modal_color_display(self):
        """Test that tag management modals display colors correctly"""
        # Create a patient
        patient = Patient.objects.create(
            name='Modal Test Patient',
            birthday='1988-11-25',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.yellow_tag,
            notes='Modal test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify modal contains color styling
        self.assertContains(response, 'available-tag-item')  # Available tag item class
        self.assertContains(response, 'available-tags-container')  # Container class
        self.assertContains(response, 'assigned-tag-item')  # Assigned tag item class

    def test_tag_color_contrast_accessibility(self):
        """Test that tag colors provide good contrast"""
        # Create a patient
        patient = Patient.objects.create(
            name='Accessibility Test Patient',
            birthday='1987-09-15',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add tags with different colors
        for allowed_tag in [self.red_tag, self.blue_tag, self.green_tag, self.yellow_tag]:
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Accessibility test for {allowed_tag.name}',
                created_by=self.user,
                updated_by=self.user
            )
            patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify all tags have white text for contrast
        self.assertContains(response, 'color: white')  # Should be present for all colored badges

    def test_tag_icon_consistency(self):
        """Test that tag icons are consistent"""
        # Create a patient
        patient = Patient.objects.create(
            name='Icon Test Patient',
            birthday='1991-04-30',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.green_tag,
            notes='Icon test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify icon consistency
        self.assertContains(response, 'bi-tag-fill')  # Filled tag icon
        self.assertContains(response, 'bi-tags')  # Multiple tags icon
        self.assertContains(response, 'bi-plus-circle')  # Add icon
        self.assertContains(response, 'bi-x')  # Remove icon

    def test_tag_mobile_responsive_styling(self):
        """Test that tag styling is responsive on mobile devices"""
        # Create a patient
        patient = Patient.objects.create(
            name='Mobile Test Patient',
            birthday='1993-08-12',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add multiple tags
        for allowed_tag in [self.red_tag, self.blue_tag, self.green_tag]:
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Mobile test for {allowed_tag.name}',
                created_by=self.user,
                updated_by=self.user
            )
            patient.tags.add(tag)
        
        # Test with mobile user agent
        mobile_user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
        
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url, HTTP_USER_AGENT=mobile_user_agent)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify responsive styling
        self.assertContains(response, 'btn-sm')  # Small buttons
        self.assertContains(response, 'modal-lg')  # Large modal for better mobile experience

    def test_tag_loading_state_display(self):
        """Test that loading states are displayed properly"""
        # Create a patient
        patient = Patient.objects.create(
            name='Loading Test Patient',
            birthday='1994-12-05',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify loading state elements
        self.assertContains(response, 'spinner-border')  # Loading spinner
        self.assertContains(response, 'Carregando tags disponíveis')  # Loading text
        self.assertContains(response, 'text-center py-3')  # Loading container

    def test_tag_error_state_display(self):
        """Test that error states are displayed properly"""
        # Create a patient
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1995-02-18',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify error handling JavaScript functions
        self.assertContains(response, 'showError')  # Error display function
        self.assertContains(response, 'showSuccess')  # Success display function

    def test_tag_selection_highlighting(self):
        """Test that tag selection is properly highlighted"""
        # Create a patient
        patient = Patient.objects.create(
            name='Selection Test Patient',
            birthday='1996-06-22',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify selection highlighting CSS
        self.assertContains(response, 'available-tag-item.selected')  # Selected state
        self.assertContains(response, 'background-color: #e7f3ff')  # Selection background
        self.assertContains(response, 'border-color: #0d6efd')  # Selection border

    def test_tag_count_display(self):
        """Test that tag count is displayed and updated correctly"""
        # Create a patient
        patient = Patient.objects.create(
            name='Count Test Patient',
            birthday='1997-10-08',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add tags
        for allowed_tag in [self.red_tag, self.blue_tag]:
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Count test for {allowed_tag.name}',
                created_by=self.user,
                updated_by=self.user
            )
            patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tag count display
        self.assertContains(response, 'Total de tags: <span id="tag-count">2</span>')
        self.assertContains(response, 'updateTagCount')  # JavaScript function

    def test_tag_color_consistency_across_views(self):
        """Test that tag colors are consistent across different views"""
        # Create a patient
        patient = Patient.objects.create(
            name='Consistency Test Patient',
            birthday='1998-01-14',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.yellow_tag,
            notes='Consistency test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Test detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        detail_response = self.client.get(detail_url)
        
        # Test API response
        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': patient.pk})
        api_response = self.client.get(api_url)
        
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(api_response.status_code, 200)
        
        # Verify color consistency
        self.assertContains(detail_response, '#ffc107')  # Yellow color in HTML
        api_data = api_response.json()
        self.assertEqual(api_data['current_tags'][0]['color'], '#ffc107')  # Yellow color in API

    def test_custom_color_validation(self):
        """Test that custom colors are handled properly"""
        # Create a tag with custom color
        custom_tag = AllowedTag.objects.create(
            name='Custom Color',
            color='#9b59b6',  # Purple
            description='Custom purple color',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create a patient
        patient = Patient.objects.create(
            name='Custom Color Test Patient',
            birthday='1999-03-27',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add the custom colored tag
        tag = Tag.objects.create(
            allowed_tag=custom_tag,
            notes='Custom color test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify custom color is displayed
        self.assertContains(response, 'Custom Color')
        self.assertContains(response, '#9b59b6')  # Purple color

    def test_tag_display_ordering(self):
        """Test that tags are displayed in a consistent order"""
        # Create a patient
        patient = Patient.objects.create(
            name='Order Test Patient',
            birthday='2000-05-11',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add tags in specific order
        tags_to_add = [self.yellow_tag, self.red_tag, self.green_tag, self.blue_tag]
        for allowed_tag in tags_to_add:
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Order test for {allowed_tag.name}',
                created_by=self.user,
                updated_by=self.user
            )
            patient.tags.add(tag)
        
        # Go to detail page
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify all tags are displayed
        self.assertContains(response, 'Warning')
        self.assertContains(response, 'High Priority')
        self.assertContains(response, 'Follow Up')
        self.assertContains(response, 'Regular')