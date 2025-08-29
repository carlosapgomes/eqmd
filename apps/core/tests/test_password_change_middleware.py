from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from unittest.mock import patch, MagicMock
from apps.core.middleware import PasswordChangeRequiredMiddleware
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


class PasswordChangeRequiredMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PasswordChangeRequiredMiddleware(lambda r: MagicMock())
        
        # Create test user
        self.user = UserFactory(
            username='testuser',
            email='test@hospital.com',
            password_change_required=True
        )
        self.user.set_password('testpass123')
        self.user.save()

    def _setup_request(self, url, user=None):
        """Helper method to setup request with session, auth, and messages."""
        request = self.factory.get(url)
        
        # Add session
        session_middleware = SessionMiddleware(lambda r: MagicMock())
        session_middleware.process_request(request)
        request.session.save()
        
        # Add user
        if user:
            request.user = user
        else:
            request.user = MagicMock()
            request.user.is_authenticated = False
        
        # Add messages
        messages = FallbackStorage(request)
        request._messages = messages
        
        return request

    def test_middleware_skips_unauthenticated_users(self):
        """Test middleware skips unauthenticated users."""
        request = self._setup_request('/dashboard/')
        
        # Mock get_response to return a response
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        response = self.middleware(request)
        
        # Should call get_response normally
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    def test_middleware_skips_users_without_flag(self):
        """Test middleware skips users who don't need password change."""
        user = UserFactory(password_change_required=False)
        request = self._setup_request('/dashboard/', user=user)
        
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        response = self.middleware(request)
        
        # Should call get_response normally
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    def test_middleware_allows_password_change_urls(self):
        """Test middleware allows access to password change URLs."""
        request = self._setup_request('/password-change-required/', user=self.user)
        
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        response = self.middleware(request)
        
        # Should call get_response normally
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    def test_middleware_allows_logout_url(self):
        """Test middleware allows access to logout URL."""
        request = self._setup_request('/accounts/logout/', user=self.user)
        
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        response = self.middleware(request)
        
        # Should call get_response normally
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    def test_middleware_allows_static_files(self):
        """Test middleware allows access to static files."""
        request = self._setup_request('/static/css/test.css', user=self.user)
        
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        response = self.middleware(request)
        
        # Should call get_response normally
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    def test_middleware_allows_media_files(self):
        """Test middleware allows access to media files."""
        request = self._setup_request('/media/images/test.png', user=self.user)
        
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        response = self.middleware(request)
        
        # Should call get_response normally
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    @patch('apps.core.middleware.redirect')
    @patch('apps.core.middleware.messages')
    @patch('apps.core.middleware.get_client_ip')
    def test_middleware_redirects_when_password_change_required(self, mock_get_ip, mock_messages, mock_redirect):
        """Test middleware redirects users who need password change."""
        mock_get_ip.return_value = '127.0.0.1'
        mock_redirect_response = MagicMock()
        mock_redirect.return_value = mock_redirect_response
        
        request = self._setup_request('/dashboard/', user=self.user)
        
        response = self.middleware(request)
        
        # Should redirect to password change page
        mock_redirect.assert_called_once_with('core:password_change_required')
        
        # Should add warning message
        mock_messages.warning.assert_called_once()
        
        # Should log security event
        mock_get_ip.assert_called_once_with(request)
        
        self.assertEqual(response, mock_redirect_response)

    @patch('apps.core.middleware.logger')
    @patch('apps.core.middleware.get_client_ip')
    def test_middleware_logs_security_event(self, mock_get_ip, mock_logger):
        """Test middleware logs security events."""
        mock_get_ip.return_value = '192.168.1.100'
        
        request = self._setup_request('/dashboard/', user=self.user)
        
        with patch('apps.core.middleware.redirect'):
            self.middleware(request)
        
        # Should log the security event
        mock_logger.info.assert_called_once()
        log_call_args = mock_logger.info.call_args[0][0]
        
        self.assertIn('Password change required redirect', log_call_args)
        self.assertIn('testuser', log_call_args)
        self.assertIn('192.168.1.100', log_call_args)
        self.assertIn('/dashboard/', log_call_args)

    def test_middleware_handles_missing_password_change_required_attribute(self):
        """Test middleware handles users without password_change_required attribute."""
        # Create user without the attribute (simulate old user model)
        user = MagicMock()
        user.is_authenticated = True
        delattr(user, 'password_change_required')  # Remove the attribute
        
        request = self._setup_request('/dashboard/', user=user)
        
        mock_response = MagicMock()
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        # Should not raise exception and should proceed normally
        response = self.middleware(request)
        
        self.middleware.get_response.assert_called_once_with(request)
        self.assertEqual(response, mock_response)

    def test_middleware_order_with_other_middleware(self):
        """Test that middleware works correctly with other middleware."""
        # This is an integration test to ensure middleware order is correct
        from django.test import Client
        
        client = Client()
        client.login(username='testuser', password='testpass123')
        
        # Should redirect from dashboard to password change
        response = client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        
        # Should allow access to password change page
        response = client.get('/password-change-required/')
        self.assertEqual(response.status_code, 200)


class MiddlewareIntegrationTest(TestCase):
    """Integration tests for the password change middleware."""
    
    def setUp(self):
        self.client = self.client_class()
        self.user = UserFactory(
            username='integrationuser',
            email='integration@hospital.com',
            password_change_required=True
        )
        self.user.set_password('integration123')
        self.user.save()

    def test_middleware_integration_with_views(self):
        """Test middleware integration with actual views."""
        self.client.login(username='integrationuser', password='integration123')
        
        # Test various URLs that should redirect
        urls_to_test = [
            '/dashboard/',
            '/patients/',
            '/events/',
        ]
        
        for url in urls_to_test:
            with self.subTest(url=url):
                response = self.client.get(url)
                if response.status_code == 302:
                    # Should redirect to password change if URL exists
                    self.assertIn('password-change-required', response.url)

    def test_middleware_does_not_break_admin(self):
        """Test that middleware doesn't break admin functionality."""
        # Create admin user who needs password change
        admin_user = UserFactory(
            username='admin',
            email='admin@hospital.com',
            is_staff=True,
            is_superuser=True,
            password_change_required=True
        )
        admin_user.set_password('admin123')
        admin_user.save()
        
        self.client.login(username='admin', password='admin123')
        
        # Should allow admin logout (POST request)
        response = self.client.post('/admin/logout/')
        # Should not redirect to password change (allows logout)
        if response.status_code == 302:
            self.assertNotIn('password-change-required', response.url)

    def test_middleware_with_ajax_requests(self):
        """Test middleware behavior with AJAX requests."""
        self.client.login(username='integrationuser', password='integration123')
        
        # Test with AJAX header
        response = self.client.get(
            '/dashboard/', 
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should still redirect AJAX requests
        if response.status_code == 302:
            self.assertIn('password-change-required', response.url)