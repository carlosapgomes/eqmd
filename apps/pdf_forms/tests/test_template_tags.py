from django.test import TestCase
from django.template import Template, Context
from django.conf import settings
from apps.pdf_forms.models import PDFFormTemplate
from apps.pdf_forms.templatetags import pdf_forms_tags
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, UserFactory
from unittest.mock import patch


class PDFFormsTemplateTagsTests(TestCase):
    """Test PDF forms template tags."""

    def setUp(self):
        self.user = UserFactory()

    def test_get_item_filter_existing_key(self):
        """Test get_item filter with existing key."""
        template = Template("{% load pdf_forms_tags %}{{ my_dict|get_item:'key1' }}")
        context = Context({'my_dict': {'key1': 'value1', 'key2': 'value2'}})
        rendered = template.render(context)
        self.assertEqual(rendered.strip(), 'value1')

    def test_get_item_filter_nonexistent_key(self):
        """Test get_item filter with nonexistent key."""
        template = Template("{% load pdf_forms_tags %}{{ my_dict|get_item:'nonexistent' }}")
        context = Context({'my_dict': {'key1': 'value1'}})
        rendered = template.render(context)
        self.assertEqual(rendered.strip(), '')

    def test_get_item_filter_none_dict(self):
        """Test get_item filter with None dictionary."""
        template = Template("{% load pdf_forms_tags %}{{ my_dict|get_item:'key1' }}")
        context = Context({'my_dict': None})
        rendered = template.render(context)
        self.assertEqual(rendered.strip(), '')

    def test_pdf_forms_enabled_tag_true(self):
        """Test pdf_forms_enabled tag when enabled."""
        with patch.object(settings, 'PDF_FORMS_CONFIG', {'enabled': True}):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_enabled %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), 'True')

    def test_pdf_forms_enabled_tag_false(self):
        """Test pdf_forms_enabled tag when disabled."""
        with patch.object(settings, 'PDF_FORMS_CONFIG', {'enabled': False}):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_enabled %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), 'False')

    def test_pdf_forms_enabled_tag_no_config(self):
        """Test pdf_forms_enabled tag when no config exists."""
        with patch.object(settings, 'PDF_FORMS_CONFIG', None):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_enabled %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), 'False')

    def test_filesizeformat_filter_bytes(self):
        """Test filesizeformat filter with bytes."""
        template = Template("{% load pdf_forms_tags %}{{ size|filesizeformat }}")
        
        # Test various byte values
        test_cases = [
            (500, '500 bytes'),
            (1024, '1.0 KB'),
            (1536, '1.5 KB'),
            (1048576, '1.0 MB'),
            (1572864, '1.5 MB'),
            (1073741824, '1.0 GB'),
            (1610612736, '1.5 GB'),
        ]
        
        for size_bytes, expected in test_cases:
            context = Context({'size': size_bytes})
            rendered = template.render(context)
            self.assertEqual(rendered.strip(), expected)

    def test_filesizeformat_filter_invalid_input(self):
        """Test filesizeformat filter with invalid input."""
        template = Template("{% load pdf_forms_tags %}{{ size|filesizeformat }}")
        
        # Test invalid inputs
        test_cases = [
            ('invalid', '0 bytes'),
            (None, '0 bytes'),
            ('not_a_number', '0 bytes'),
            ([], '0 bytes'),
        ]
        
        for invalid_input, expected in test_cases:
            context = Context({'size': invalid_input})
            rendered = template.render(context)
            self.assertEqual(rendered.strip(), expected)

    def test_pdf_forms_menu_tag_with_request(self):
        """Test pdf_forms_menu tag with request context."""
        template = Template("{% load pdf_forms_tags %}{% pdf_forms_menu %}")
        request = Mock()
        request.user = self.user
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', {'enabled': True}):
            context = Context({'request': request})
            rendered = template.render(context)
            
            # Should contain the user and enabled flag in context
            self.assertIn('user', rendered)
            self.assertIn('enabled', rendered)

    def test_pdf_forms_menu_tag_without_request(self):
        """Test pdf_forms_menu tag without request context."""
        template = Template("{% load pdf_forms_tags %}{% pdf_forms_menu %}")
        
        # Should handle missing request gracefully
        context = Context({})
        rendered = template.render(context)
        
        # Should not raise an exception
        self.assertIsInstance(rendered, str)

    def test_get_pdf_form_count_tag(self):
        """Test get_pdf_form_count tag."""
        # Create some templates
        PDFFormTemplateFactory(is_active=True, hospital_specific=True)
        PDFFormTemplateFactory(is_active=True, hospital_specific=True)
        PDFFormTemplateFactory(is_active=False, hospital_specific=True)  # Should not be counted
        PDFFormTemplateFactory(is_active=True, hospital_specific=False)  # Should not be counted
        
        template = Template("{% load pdf_forms_tags %}{% get_pdf_form_count %}")
        rendered = template.render(Context({}))
        
        # Should count only active, hospital-specific templates
        self.assertEqual(rendered.strip(), '2')

    def test_get_pdf_form_count_tag_no_templates(self):
        """Test get_pdf_form_count tag with no templates."""
        # Ensure no templates exist
        PDFFormTemplate.objects.all().delete()
        
        template = Template("{% load pdf_forms_tags %}{% get_pdf_form_count %}")
        rendered = template.render(Context({}))
        
        self.assertEqual(rendered.strip(), '0')

    def test_pdf_forms_config_tag_with_key(self):
        """Test pdf_forms_config tag with specific key."""
        config = {
            'enabled': True,
            'max_file_size': 1048576,
            'templates_path': '/path/to/templates'
        }
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_config 'max_file_size' %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), '1048576')

    def test_pdf_forms_config_tag_without_key(self):
        """Test pdf_forms_config tag without specific key."""
        config = {
            'enabled': True,
            'max_file_size': 1048576
        }
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_config %}")
            rendered = template.render(Context({}))
            
            # Should return the entire config as string representation
            self.assertIn("'enabled': True", rendered)
            self.assertIn("'max_file_size': 1048576", rendered)

    def test_pdf_forms_config_tag_no_config(self):
        """Test pdf_forms_config tag with no config."""
        with patch.object(settings, 'PDF_FORMS_CONFIG', None):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_config 'enabled' %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), 'None')

    def test_pdf_forms_config_tag_nonexistent_key(self):
        """Test pdf_forms_config tag with nonexistent key."""
        config = {'enabled': True}
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_config 'nonexistent' %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), 'None')

    def test_pdf_forms_max_file_size_tag(self):
        """Test pdf_forms_max_file_size tag."""
        config = {'max_file_size': 2097152}  # 2MB
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_max_file_size %}")
            rendered = template.render(Context({}))
            self.assertEqual(rendered.strip(), '2097152')

    def test_pdf_forms_max_file_size_tag_default(self):
        """Test pdf_forms_max_file_size tag with default value."""
        with patch.object(settings, 'PDF_FORMS_CONFIG', {}):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_max_file_size %}")
            rendered = template.render(Context({})
)
            # Should return default value (10MB)
            self.assertEqual(rendered.strip(), '10485760')

    def test_pdf_forms_max_file_size_tag_no_config(self):
        """Test pdf_forms_max_file_size tag with no config."""
        with patch.object(settings, 'PDF_FORMS_CONFIG', None):
            template = Template("{% load pdf_forms_tags %}{% pdf_forms_max_file_size %}")
            rendered = template.render(Context({}))
            
            # Should return default value (10MB)
            self.assertEqual(rendered.strip(), '10485760')

    def test_pdf_form_file_size_check_filter_within_limit(self):
        """Test pdf_form_file_size_check filter with file within limit."""
        config = {'max_file_size': 1048576}  # 1MB
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{{ file_size|pdf_form_file_size_check }}")
            
            # Test with file size under limit
            context = Context({'file_size': 512000})  # 500KB
            rendered = template.render(context)
            self.assertEqual(rendered.strip(), 'True')

    def test_pdf_form_file_size_check_filter_over_limit(self):
        """Test pdf_form_file_size_check filter with file over limit."""
        config = {'max_file_size': 1048576}  # 1MB
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{{ file_size|pdf_form_file_size_check }}")
            
            # Test with file size over limit
            context = Context({'file_size': 2097152})  # 2MB
            rendered = template.render(context)
            self.assertEqual(rendered.strip(), 'False')

    def test_pdf_form_file_size_check_filter_equal_to_limit(self):
        """Test pdf_form_file_size_check filter with file size equal to limit."""
        config = {'max_file_size': 1048576}  # 1MB
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            template = Template("{% load pdf_forms_tags %}{{ file_size|pdf_form_file_size_check }}")
            
            # Test with file size equal to limit
            context = Context({'file_size': 1048576})  # 1MB
            rendered = template.render(context)
            self.assertEqual(rendered.strip(), 'True')

    def test_template_tag_error_handling(self):
        """Test error handling in template tags."""
        # Test with invalid inputs that shouldn't raise exceptions
        template = Template("{% load pdf_forms_tags %}{{ invalid_dict|get_item:'key' }}")
        context = Context({'invalid_dict': 'not_a_dict'})
        rendered = template.render(context)
        
        # Should not raise an exception
        self.assertIsInstance(rendered, str)

    def test_multiple_tags_in_one_template(self):
        """Test using multiple tags in one template."""
        template = Template("""
            {% load pdf_forms_tags %}
            Enabled: {% pdf_forms_enabled %}
            Count: {% get_pdf_form_count %}
            Max size: {% pdf_forms_max_file_size %}
        """)
        
        config = {'enabled': True, 'max_file_size': 1048576}
        
        with patch.object(settings, 'PDF_FORMS_CONFIG', config):
            rendered = template.render(Context({}))
            
            # All tags should work together
            self.assertIn('Enabled:', rendered)
            self.assertIn('Count:', rendered)
            self.assertIn('Max size:', rendered)