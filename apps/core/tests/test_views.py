"""
Tests for the core app views.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.tests.factories import (
    UserFactory,
    DoctorFactory,
    ResidentFactory,
    NurseFactory,
)

User = get_user_model()


class LandingPageViewTestCase(TestCase):
    """Test cases for the landing page view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

    def test_landing_page_accessible(self):
        """Test that landing page is accessible without authentication."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_landing_page_content(self):
        """Test that landing page contains expected content."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EquipeMed')
        self.assertContains(response, 'Conecte sua equipe médica')
        self.assertContains(response, 'Acessar Plataforma')

    def test_landing_page_template_used(self):
        """Test that correct template is used."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertTemplateUsed(response, 'core/landing_page.html')

    def test_landing_page_context(self):
        """Test that landing page provides correct context."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_title', response.context)
        self.assertEqual(response.context['page_title'], 'Bem-vindo ao EquipeMed')

    def test_landing_page_login_links(self):
        """Test that landing page contains login links."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for login URL in the response
        login_url = reverse('account_login')
        self.assertContains(response, login_url)

    def test_landing_page_navigation(self):
        """Test landing page navigation elements."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'navbar')
        self.assertContains(response, 'Entrar')

    def test_landing_page_features_section(self):
        """Test that landing page contains features section."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rastreamento de Pacientes')
        self.assertContains(response, 'Gestão de Eventos Clínicos')

    def test_landing_page_cta_sections(self):
        """Test that landing page contains call-to-action sections."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Começar Agora')
        self.assertContains(response, 'Pronto para Transformar')

    def test_landing_page_footer(self):
        """Test that landing page contains footer information."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EquipeMed')
        # Footer should be inherited from base template

    def test_landing_page_responsive_elements(self):
        """Test that landing page contains responsive elements."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'col-lg-')
        self.assertContains(response, 'container')

    def test_landing_page_multiple_requests(self):
        """Test multiple requests to landing page."""
        url = reverse('core:landing_page')
        
        response1 = self.client.get(url)
        response2 = self.client.get(url)
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

    def test_landing_page_head_elements(self):
        """Test that landing page has proper head elements."""
        url = reverse('core:landing_page')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should inherit from base template
        self.assertContains(response, '<title>')
        self.assertContains(response, 'viewport')


class DashboardViewTestCase(TestCase):
    """Test cases for the dashboard view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = UserFactory(
            username='testuser',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

    def test_dashboard_requires_authentication(self):
        """Test that dashboard requires user authentication."""
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_dashboard_accessible_when_authenticated(self):
        """Test that dashboard is accessible for authenticated users."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_dashboard_content_authenticated(self):
        """Test dashboard content for authenticated users."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bem-vindo')
        self.assertContains(response, 'Painel de controle')
        self.assertContains(response, 'EquipeMed')

    def test_dashboard_template_used(self):
        """Test that correct template is used for dashboard."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertTemplateUsed(response, 'core/dashboard.html')

    def test_dashboard_context(self):
        """Test that dashboard provides correct context."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_title', response.context)
        self.assertEqual(response.context['page_title'], 'Painel Principal')

    def test_dashboard_navigation_elements(self):
        """Test that dashboard contains navigation elements."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sidebar')
        self.assertContains(response, 'navbar')
        self.assertContains(response, 'Dashboard')

    def test_dashboard_user_menu(self):
        """Test that dashboard contains user menu."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dropdown')
        logout_url = reverse('account_logout')
        self.assertContains(response, logout_url)


class TemplatesHubViewTestCase(TestCase):
    """Test cases for the templates hub view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.doctor = DoctorFactory(password='testpass123')
        self.resident = ResidentFactory(password='testpass123')
        self.nurse = NurseFactory(password='testpass123')

    def test_templates_hub_requires_authentication(self):
        """Test that templates hub requires authentication."""
        response = self.client.get(reverse('core:templates_hub'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_templates_hub_accessible_to_doctor(self):
        """Test that templates hub is accessible to doctors."""
        self.client.login(username=self.doctor.username, password='testpass123')
        response = self.client.get(reverse('core:templates_hub'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/templates_hub.html')

    def test_templates_hub_accessible_to_resident(self):
        """Test that templates hub is accessible to residents."""
        self.client.login(username=self.resident.username, password='testpass123')
        response = self.client.get(reverse('core:templates_hub'))
        self.assertEqual(response.status_code, 200)

    def test_templates_hub_forbidden_for_non_privileged(self):
        """Test that templates hub is forbidden for non-privileged users."""
        self.client.login(username=self.nurse.username, password='testpass123')
        response = self.client.get(reverse('core:templates_hub'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_sidebar_navigation(self):
        """Test that dashboard contains sidebar navigation."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lista de Pacientes')
        self.assertContains(response, 'Novo Paciente')
        self.assertContains(response, 'Eventos Clínicos')

    def test_dashboard_stats_section(self):
        """Test that dashboard contains stats section."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for stats cards or similar elements
        self.assertContains(response, 'card')

    def test_dashboard_mobile_responsive(self):
        """Test that dashboard is mobile responsive."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'd-lg-none')  # Mobile-specific classes
        self.assertContains(response, 'offcanvas')  # Mobile menu

    def test_dashboard_different_users(self):
        """Test dashboard for different users."""
        # Test with first user
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        
        # Logout and test with different user
        self.client.logout()
        other_user = UserFactory(username='otheruser', password='testpass123')
        self.client.login(username='otheruser', password='testpass123')
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)

    def test_dashboard_session_handling(self):
        """Test dashboard session handling."""
        # Login and access dashboard
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Logout and try to access again
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_dashboard_inactive_user(self):
        """Test dashboard access for inactive user."""
        self.user.is_active = False
        self.user.save()
        
        # Try to login with inactive user
        login_successful = self.client.login(username='testuser', password='testpass123')
        self.assertFalse(login_successful)
        
        # Try to access dashboard
        url = reverse('core:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_dashboard_staff_user(self):
        """Test dashboard for staff user."""
        staff_user = UserFactory(username='staffuser', is_staff=True, password='testpass123')
        self.client.login(username='staffuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Staff users should have same access to dashboard

    def test_dashboard_superuser(self):
        """Test dashboard for superuser."""
        superuser = UserFactory(username='superuser', is_superuser=True, is_staff=True, password='testpass123')
        self.client.login(username='superuser', password='testpass123')
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Superusers should have same access to dashboard
