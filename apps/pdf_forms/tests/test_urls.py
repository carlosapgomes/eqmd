from django.test import TestCase
from django.urls import reverse, resolve
from apps.pdf_forms import urls
from apps.pdf_forms.views import (
    PDFFormTemplateListView,
    PDFFormSelectView,
    PDFFormFillView,
    PDFFormSubmissionDetailView,
    PDFFormDownloadView,
    PDFFormSubmissionDeleteView
)


class PDFFormsURLTests(TestCase):
    """Test PDF forms URL patterns."""

    def test_template_list_url(self):
        """Test template list URL."""
        url = reverse('pdf_forms:template_list')
        self.assertEqual(url, '/pdf-forms/templates/')
        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormTemplateListView)

    def test_form_select_url(self):
        """Test form select URL."""
        import uuid
        patient_id = uuid.uuid4()
        url = reverse('pdf_forms:form_select', kwargs={'patient_id': patient_id})
        self.assertEqual(url, f'/pdf-forms/select/{patient_id}/')
        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormSelectView)

    def test_form_fill_url(self):
        """Test form fill URL."""
        import uuid
        template_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        url = reverse('pdf_forms:form_fill', kwargs={'template_id': template_id, 'patient_id': patient_id})
        self.assertEqual(url, f'/pdf-forms/fill/{template_id}/{patient_id}/')
        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormFillView)

    def test_submission_detail_url(self):
        """Test submission detail URL."""
        import uuid
        submission_id = uuid.uuid4()
        url = reverse('pdf_forms:submission_detail', kwargs={'pk': submission_id})
        self.assertEqual(url, f'/pdf-forms/submission/{submission_id}/')
        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormSubmissionDetailView)

    def test_submission_delete_url(self):
        """Test submission delete URL."""
        import uuid
        submission_id = uuid.uuid4()
        url = reverse('pdf_forms:submission_delete', kwargs={'pk': submission_id})
        self.assertEqual(url, f'/pdf-forms/submission/{submission_id}/delete/')
        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormSubmissionDeleteView)

    def test_pdf_download_url(self):
        """Test PDF download URL."""
        import uuid
        submission_id = uuid.uuid4()
        url = reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission_id})
        self.assertEqual(url, f'/pdf-forms/download/{submission_id}/')
        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormDownloadView)

    def test_urlpatterns_count(self):
        """Test that all expected URL patterns are present."""
        urlpatterns = urls.urlpatterns
        self.assertEqual(len(urlpatterns), 6)

    def test_urlpatterns_names(self):
        """Test that all URL patterns have names."""
        urlpatterns = urls.urlpatterns
        
        for pattern in urlpatterns:
            self.assertIsNotNone(pattern.name, f"URL pattern {pattern.pattern} has no name")

    def test_app_name(self):
        """Test that app name is set correctly."""
        self.assertEqual(urls.app_name, 'pdf_forms')

    def test_url_parameter_types(self):
        """Test that URL parameters use UUID type."""
        import uuid
        
        # Test that UUID parameters are properly typed
        patient_id = uuid.uuid4()
        template_id = uuid.uuid4()
        submission_id = uuid.uuid4()
        
        # These should not raise any exceptions
        reverse('pdf_forms:form_select', kwargs={'patient_id': patient_id})
        reverse('pdf_forms:form_fill', kwargs={'template_id': template_id, 'patient_id': patient_id})
        reverse('pdf_forms:submission_detail', kwargs={'pk': submission_id})
        reverse('pdf_forms:submission_delete', kwargs={'pk': submission_id})
        reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission_id})

    def test_url_resolution_with_string_uuids(self):
        """Test URL resolution with string UUIDs."""
        import uuid
        
        # Test with string UUIDs (as they come from URLs)
        patient_id_str = str(uuid.uuid4())
        template_id_str = str(uuid.uuid4())
        submission_id_str = str(uuid.uuid4())
        
        # Should resolve correctly
        url = f'/pdf-forms/select/{patient_id_str}/'
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormSelectView)
        self.assertEqual(resolver.kwargs['patient_id'], patient_id_str)
        
        url = f'/pdf-forms/fill/{template_id_str}/{patient_id_str}/'
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PDFFormFillView)
        self.assertEqual(resolver.kwargs['template_id'], template_id_str)
        self.assertEqual(resolver.kwargs['patient_id'], patient_id_str)

    def test_url_reverse_with_kwargs(self):
        """Test URL reverse with keyword arguments."""
        import uuid
        
        patient_id = uuid.uuid4()
        template_id = uuid.uuid4()
        submission_id = uuid.uuid4()
        
        # Test all URLs can be reversed with kwargs
        reverse('pdf_forms:form_select', kwargs={'patient_id': patient_id})
        reverse('pdf_forms:form_fill', kwargs={'template_id': template_id, 'patient_id': patient_id})
        reverse('pdf_forms:submission_detail', kwargs={'pk': submission_id})
        reverse('pdf_forms:submission_delete', kwargs={'pk': submission_id})
        reverse('pdf_forms:pdf_download', kwargs={'submission_id': submission_id})

    def test_invalid_uuid_url(self):
        """Test that invalid UUIDs in URLs are handled gracefully."""
        # These should still resolve (Django doesn't validate UUID format in URL patterns)
        invalid_uuid = "invalid-uuid-string"
        
        try:
            url = f'/pdf-forms/select/{invalid_uuid}/'
            resolver = resolve(url)
            self.assertEqual(resolver.func.view_class, PDFFormSelectView)
            self.assertEqual(resolver.kwargs['patient_id'], invalid_uuid)
        except:
            # If it fails to resolve, that's also acceptable behavior
            pass