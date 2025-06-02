"""
Tests for the core app templates.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.template.loader import get_template
from django.template import Context, Template
from django.contrib.auth import get_user_model
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


class TemplateTestCase(TestCase):
    """Test cases for core app templates."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory(password='testpass123')

    def test_landing_page_template_exists(self):
        """Test that landing page template exists and can be loaded."""
        template = get_template('core/landing_page.html')
        self.assertIsNotNone(template)

    def test_dashboard_template_exists(self):
        """Test that dashboard template exists and can be loaded."""
        template = get_template('core/dashboard.html')
        self.assertIsNotNone(template)

    def test_landing_page_template_inheritance(self):
        """Test that landing page template extends base template."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain elements from base template
        self.assertContains(response, '<html')
        self.assertContains(response, '</html>')
        self.assertContains(response, 'EquipeMed')

    def test_dashboard_template_inheritance(self):
        """Test that dashboard template extends base_app template."""
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain elements from base_app template
        self.assertContains(response, 'sidebar')
        self.assertContains(response, 'navbar')

    def test_landing_page_template_blocks(self):
        """Test that landing page template properly uses template blocks."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain custom header block content
        self.assertContains(response, 'navbar')
        self.assertContains(response, 'Entrar')
        
        # Should contain custom content block
        self.assertContains(response, 'Conecte sua equipe médica')

    def test_dashboard_template_blocks(self):
        """Test that dashboard template properly uses template blocks."""
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain app_content block content
        self.assertContains(response, 'Bem-vindo')
        self.assertContains(response, 'Painel de controle')

    def test_landing_page_responsive_elements(self):
        """Test that landing page contains responsive elements."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain Bootstrap responsive classes
        self.assertContains(response, 'container')
        self.assertContains(response, 'row')
        self.assertContains(response, 'col-')

    def test_dashboard_responsive_elements(self):
        """Test that dashboard contains responsive elements."""
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain responsive navigation
        self.assertContains(response, 'd-lg-none')
        self.assertContains(response, 'offcanvas')

    def test_landing_page_navigation_elements(self):
        """Test that landing page contains proper navigation elements."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain navigation bar
        self.assertContains(response, 'navbar')
        self.assertContains(response, 'navbar-brand')
        
        # Should contain login link
        login_url = reverse('account_login')
        self.assertContains(response, login_url)

    def test_dashboard_navigation_elements(self):
        """Test that dashboard contains proper navigation elements."""
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain sidebar navigation
        self.assertContains(response, 'sidebar')
        self.assertContains(response, 'nav-link')
        
        # Should contain user menu
        self.assertContains(response, 'dropdown')
        logout_url = reverse('account_logout')
        self.assertContains(response, logout_url)

    def test_landing_page_hero_section(self):
        """Test that landing page contains hero section."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain hero content
        self.assertContains(response, 'Conecte sua equipe médica')
        self.assertContains(response, 'display-4')
        self.assertContains(response, 'btn-medical-primary')

    def test_landing_page_features_section(self):
        """Test that landing page contains features section."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain feature cards
        self.assertContains(response, 'Rastreamento de Pacientes')
        self.assertContains(response, 'Gestão de Eventos Clínicos')
        self.assertContains(response, 'card')

    def test_landing_page_cta_sections(self):
        """Test that landing page contains call-to-action sections."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain CTA buttons
        self.assertContains(response, 'Acessar Plataforma')
        self.assertContains(response, 'Começar Agora')

    def test_dashboard_welcome_section(self):
        """Test that dashboard contains welcome section."""
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain welcome message
        self.assertContains(response, 'Bem-vindo')
        self.assertContains(response, 'Painel de controle')

    def test_dashboard_stats_section(self):
        """Test that dashboard contains stats section."""
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain stats cards
        self.assertContains(response, 'card')

    def test_template_context_variables(self):
        """Test that templates receive correct context variables."""
        # Test landing page context
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_title', response.context)
        
        # Test dashboard context
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_title', response.context)

    def test_template_static_files(self):
        """Test that templates properly load static files."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain static file references
        self.assertContains(response, 'static')

    def test_template_bootstrap_integration(self):
        """Test that templates properly integrate Bootstrap."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain Bootstrap classes
        self.assertContains(response, 'btn')
        self.assertContains(response, 'container')
        self.assertContains(response, 'navbar')

    def test_template_icons(self):
        """Test that templates contain proper icons."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain Bootstrap icons
        self.assertContains(response, 'bi-')

    def test_template_accessibility(self):
        """Test that templates contain accessibility features."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)

        # Should contain accessibility attributes
        self.assertContains(response, 'role=')

    def test_template_meta_tags(self):
        """Test that templates contain proper meta tags."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain viewport meta tag
        self.assertContains(response, 'viewport')
        self.assertContains(response, 'charset')

    def test_template_title_tags(self):
        """Test that templates contain proper title tags."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain title tag
        self.assertContains(response, '<title>')
        self.assertContains(response, 'EquipeMed')

    def test_template_language_attributes(self):
        """Test that templates contain proper language attributes."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain language attribute
        self.assertContains(response, 'lang="pt-br"')

    def test_template_custom_css_classes(self):
        """Test that templates contain custom CSS classes."""
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain medical-themed CSS classes
        self.assertContains(response, 'text-medical-')
        self.assertContains(response, 'btn-medical-')

    def test_template_form_elements(self):
        """Test that templates contain proper form elements where needed."""
        # Landing page should have links to login forms
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain form-related links
        self.assertContains(response, 'href=')

    def test_template_error_handling(self):
        """Test template error handling."""
        # Templates should handle missing context gracefully
        # This is more of a defensive test
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)
        
        # Should not contain template error indicators
        self.assertNotContains(response, 'TemplateSyntaxError')
        self.assertNotContains(response, 'VariableDoesNotExist')

    def test_template_performance(self):
        """Test template rendering performance."""
        import time
        
        start_time = time.time()
        response = self.client.get(reverse('core:landing_page'))
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        # Template rendering should be fast (less than 1 second)
        self.assertLess(end_time - start_time, 1.0)
