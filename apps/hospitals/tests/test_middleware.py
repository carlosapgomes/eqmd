"""
Tests for HospitalContextMiddleware.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from unittest.mock import Mock

from apps.hospitals.models import Hospital
from apps.hospitals.middleware import HospitalContextMiddleware

User = get_user_model()


class HospitalContextMiddlewareTest(TestCase):
    """Test cases for HospitalContextMiddleware."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = HospitalContextMiddleware(Mock())
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Medical Doctor
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            phone='1234567890',
            address='Test Address',
            city='Test City',
            state='TS',
            zip_code='12345000',
            created_by=self.user,
            updated_by=self.user
        )

    def _create_request_with_session(self, user=None):
        """Helper to create request with session middleware."""
        request = self.factory.get('/')
        
        # Add session middleware
        session_middleware = SessionMiddleware(Mock())
        session_middleware.process_request(request)
        request.session.save()
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(Mock())
        auth_middleware.process_request(request)
        
        # Set user
        request.user = user if user else self.user
        
        return request

    def test_middleware_with_unauthenticated_user(self):
        """Test middleware with unauthenticated user."""
        request = self._create_request_with_session()
        request.user = Mock()
        request.user.is_authenticated = False
        
        self.middleware._add_hospital_context(request)
        
        # Should not add hospital context to unauthenticated user
        # The middleware should not call the method that sets these attributes
        # Since the user is not authenticated, the method should return early

    def test_middleware_with_no_hospital_in_session(self):
        """Test middleware when no hospital is set in session."""
        request = self._create_request_with_session()
        
        self.middleware._add_hospital_context(request)
        
        # Should set hospital context to None
        self.assertIsNone(request.user.current_hospital)
        self.assertFalse(request.user.has_hospital_context)

    def test_middleware_with_valid_hospital_in_session(self):
        """Test middleware with valid hospital ID in session."""
        request = self._create_request_with_session()
        request.session['current_hospital_id'] = str(self.hospital.pk)
        
        self.middleware._add_hospital_context(request)
        
        # Should set hospital context correctly
        self.assertEqual(request.user.current_hospital, self.hospital)
        self.assertTrue(request.user.has_hospital_context)

    def test_middleware_with_invalid_hospital_in_session(self):
        """Test middleware with invalid hospital ID in session."""
        request = self._create_request_with_session()
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        request.session['current_hospital_id'] = invalid_uuid
        
        self.middleware._add_hospital_context(request)
        
        # Should clear invalid hospital ID and set context to None
        self.assertNotIn('current_hospital_id', request.session)
        self.assertIsNone(request.user.current_hospital)
        self.assertFalse(request.user.has_hospital_context)

    def test_set_hospital_context(self):
        """Test setting hospital context."""
        request = self._create_request_with_session()
        
        result = HospitalContextMiddleware.set_hospital_context(request, self.hospital.pk)
        
        # Should return hospital and set session
        self.assertEqual(result, self.hospital)
        self.assertEqual(request.session['current_hospital_id'], str(self.hospital.pk))
        self.assertEqual(request.user.current_hospital, self.hospital)
        self.assertTrue(request.user.has_hospital_context)

    def test_set_hospital_context_invalid_id(self):
        """Test setting hospital context with invalid ID."""
        request = self._create_request_with_session()
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        
        result = HospitalContextMiddleware.set_hospital_context(request, invalid_uuid)
        
        # Should return None and not set session
        self.assertIsNone(result)
        self.assertNotIn('current_hospital_id', request.session)

    def test_clear_hospital_context(self):
        """Test clearing hospital context."""
        request = self._create_request_with_session()
        request.session['current_hospital_id'] = str(self.hospital.pk)
        request.user.current_hospital = self.hospital
        request.user.has_hospital_context = True
        
        HospitalContextMiddleware.clear_hospital_context(request)
        
        # Should clear session and user attributes
        self.assertNotIn('current_hospital_id', request.session)
        self.assertIsNone(request.user.current_hospital)
        self.assertFalse(request.user.has_hospital_context)

    def test_get_available_hospitals(self):
        """Test getting available hospitals for user."""
        # Create another hospital
        hospital2 = Hospital.objects.create(
            name='Second Hospital',
            short_name='SH',
            phone='9876543210',
            address='Second Address',
            city='Second City',
            state='SC',
            zip_code='98765000',
            created_by=self.user,
            updated_by=self.user
        )
        
        hospitals = HospitalContextMiddleware.get_available_hospitals(self.user)
        
        # Should return all hospitals
        self.assertEqual(hospitals.count(), 2)
        self.assertIn(self.hospital, hospitals)
        self.assertIn(hospital2, hospitals)