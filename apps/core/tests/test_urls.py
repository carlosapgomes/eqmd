"""
Tests for the core app URL patterns.
"""
from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model
from apps.core import views
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


class CoreURLsTestCase(TestCase):
    """Test cases for core app URL patterns."""

    def test_landing_page_url_resolves(self):
        """Test that landing page URL resolves correctly."""
        url = reverse('core:landing_page')
        self.assertEqual(url, '/')

    def test_dashboard_url_resolves(self):
        """Test that dashboard URL resolves correctly."""
        url = reverse('core:dashboard')
        self.assertEqual(url, '/dashboard/')

    def test_landing_page_view_resolves(self):
        """Test that landing page URL resolves to correct view."""
        view = resolve('/')
        self.assertEqual(view.func, views.landing_page)
        self.assertEqual(view.view_name, 'core:landing_page')

    def test_dashboard_view_resolves(self):
        """Test that dashboard URL resolves to correct view."""
        view = resolve('/dashboard/')
        self.assertEqual(view.func, views.dashboard_view)
        self.assertEqual(view.view_name, 'core:dashboard')

    def test_url_namespace(self):
        """Test that URLs use correct namespace."""
        landing_url = reverse('core:landing_page')
        dashboard_url = reverse('core:dashboard')
        
        self.assertEqual(landing_url, '/')
        self.assertEqual(dashboard_url, '/dashboard/')

    def test_alternative_namespace(self):
        """Test that alternative namespace works."""
        # Test with full namespace
        landing_url = reverse('apps.core:landing_page')
        dashboard_url = reverse('apps.core:dashboard')
        
        self.assertEqual(landing_url, '/')
        self.assertEqual(dashboard_url, '/dashboard/')

    def test_url_patterns_accessibility(self):
        """Test URL patterns accessibility."""
        # Test landing page (should be accessible)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Test dashboard (should redirect to login)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_url_patterns_with_trailing_slash(self):
        """Test URL patterns with trailing slashes."""
        # Dashboard should work with trailing slash
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test without trailing slash (Django should redirect)
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 301)  # Permanent redirect

    def test_invalid_urls(self):
        """Test that invalid URLs return 404."""
        invalid_urls = [
            '/nonexistent/',
            '/dashboard/invalid/',
            '/random-page/',
        ]
        
        for url in invalid_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

    def test_url_reversing_in_views(self):
        """Test URL reversing functionality."""
        from django.urls import reverse
        
        # Test that reverse works correctly
        landing_url = reverse('core:landing_page')
        dashboard_url = reverse('core:dashboard')
        
        self.assertEqual(landing_url, '/')
        self.assertEqual(dashboard_url, '/dashboard/')

    def test_url_patterns_case_sensitivity(self):
        """Test URL patterns case sensitivity."""
        # URLs should be case sensitive
        response = self.client.get('/Dashboard/')
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get('/DASHBOARD/')
        self.assertEqual(response.status_code, 404)

    def test_url_patterns_with_query_parameters(self):
        """Test URL patterns with query parameters."""
        # Landing page with query parameters
        response = self.client.get('/?ref=test')
        self.assertEqual(response.status_code, 200)
        
        # Dashboard with query parameters (should still redirect to login)
        response = self.client.get('/dashboard/?tab=patients')
        self.assertEqual(response.status_code, 302)

    def test_url_patterns_with_fragments(self):
        """Test URL patterns with fragments."""
        # Fragments are handled client-side, so server should ignore them
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_url_resolution_performance(self):
        """Test URL resolution performance."""
        import time
        
        start_time = time.time()
        for _ in range(100):
            reverse('core:landing_page')
            reverse('core:dashboard')
        end_time = time.time()
        
        # URL resolution should be fast (less than 1 second for 100 iterations)
        self.assertLess(end_time - start_time, 1.0)

    def test_url_patterns_with_authentication(self):
        """Test URL patterns with different authentication states."""
        user = UserFactory(password='testpass123')
        
        # Test unauthenticated access
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        
        # Test authenticated access
        self.client.login(username=user.username, password='testpass123')
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_url_include_pattern(self):
        """Test that core URLs are properly included in main URLconf."""
        # This tests the include pattern in config/urls.py
        from django.conf import settings
        from django.urls import include
        
        # The core URLs should be included at root level
        landing_url = reverse('core:landing_page')
        self.assertEqual(landing_url, '/')

    def test_url_app_name_configuration(self):
        """Test that app_name is properly configured."""
        from apps.core.urls import app_name
        
        # Should be either 'core' or 'apps.core'
        self.assertIn(app_name, ['core', 'apps.core'])

    def test_url_patterns_list(self):
        """Test that URL patterns list is properly configured."""
        from apps.core.urls import urlpatterns
        
        # Should have exactly 2 URL patterns
        self.assertEqual(len(urlpatterns), 2)
        
        # Check pattern names
        pattern_names = [pattern.name for pattern in urlpatterns]
        self.assertIn('landing_page', pattern_names)
        self.assertIn('dashboard', pattern_names)

    def test_url_view_imports(self):
        """Test that views are properly imported in URLs."""
        from apps.core.urls import urlpatterns
        from apps.core import views
        
        # Check that views are properly referenced
        for pattern in urlpatterns:
            if hasattr(pattern, 'callback'):
                # Should be a function from views module
                self.assertTrue(hasattr(views, pattern.callback.__name__))

    def test_url_patterns_regex(self):
        """Test URL pattern regex matching."""
        # Test exact matches
        view = resolve('/')
        self.assertEqual(view.view_name, 'core:landing_page')
        
        view = resolve('/dashboard/')
        self.assertEqual(view.view_name, 'core:dashboard')

    def test_url_patterns_with_special_characters(self):
        """Test URL patterns with special characters."""
        # URLs with special characters should return 404
        special_urls = [
            '/invalid@page/',
            '/invalid#page/',
            '/invalid%page/',
        ]

        for url in special_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

    def test_url_redirect_behavior(self):
        """Test URL redirect behavior."""
        user = UserFactory(password='testpass123')
        
        # Test login redirect
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertIn('next=/dashboard/', response.url)

    def test_url_patterns_http_methods(self):
        """Test URL patterns with different HTTP methods."""
        # GET should work
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # POST should also work (though views might not handle it)
        response = self.client.post('/')
        self.assertEqual(response.status_code, 200)
        
        # Other methods should work at URL level
        response = self.client.head('/')
        self.assertEqual(response.status_code, 200)
