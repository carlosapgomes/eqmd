"""
Tests for permission decorators.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from unittest.mock import Mock, patch

from apps.core.permissions.decorators import (
    patient_access_required,
    doctor_required,
    can_edit_event_required,
    patient_data_change_required,
    can_delete_event_required,
)
from apps.core.permissions.constants import MEDICAL_DOCTOR, NURSE, STUDENT

User = get_user_model()


class PermissionDecoratorsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR
        )
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=User.NURSE
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            profession_type=User.STUDENT
        )

    def test_patient_access_required_decorator_allowed(self):
        """Test patient access decorator allows authorized users"""
        @patient_access_required
        def test_view(request, patient_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.doctor
        
        with patch('apps.core.permissions.decorators.can_access_patient', return_value=True):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_patient = Mock()
                mock_get.return_value = mock_patient
                
                response = test_view(request, patient_id='123')
                self.assertEqual(response.status_code, 200)

    def test_patient_access_required_decorator_denied(self):
        """Test patient access decorator denies unauthorized users"""
        @patient_access_required
        def test_view(request, patient_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.student
        
        with patch('apps.core.permissions.decorators.can_access_patient', return_value=False):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_patient = Mock()
                mock_get.return_value = mock_patient
                
                response = test_view(request, patient_id='123')
                self.assertIsInstance(response, HttpResponseForbidden)

    def test_doctor_required_decorator_allowed(self):
        """Test doctor required decorator allows doctors"""
        @doctor_required
        def test_view(request):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.doctor
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)

    def test_doctor_required_decorator_denied(self):
        """Test doctor required decorator denies non-doctors"""
        @doctor_required
        def test_view(request):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.nurse
        
        response = test_view(request)
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_can_edit_event_required_decorator_allowed(self):
        """Test can edit event decorator allows authorized users"""
        @can_edit_event_required
        def test_view(request, event_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.doctor
        
        with patch('apps.core.permissions.decorators.can_edit_event', return_value=True):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_event = Mock()
                mock_get.return_value = mock_event
                
                response = test_view(request, event_id='123')
                self.assertEqual(response.status_code, 200)

    def test_can_edit_event_required_decorator_denied(self):
        """Test can edit event decorator denies unauthorized users"""
        @can_edit_event_required
        def test_view(request, event_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.nurse
        
        with patch('apps.core.permissions.decorators.can_edit_event', return_value=False):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_event = Mock()
                mock_get.return_value = mock_event
                
                response = test_view(request, event_id='123')
                self.assertIsInstance(response, HttpResponseForbidden)

    def test_patient_data_change_required_decorator_allowed(self):
        """Test patient data change decorator allows authorized users"""
        @patient_data_change_required
        def test_view(request, patient_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.doctor

        with patch('apps.core.permissions.decorators.can_change_patient_personal_data', return_value=True):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_patient = Mock()
                mock_get.return_value = mock_patient

                response = test_view(request, patient_id='123')
                self.assertEqual(response.status_code, 200)

    def test_patient_data_change_required_decorator_denied(self):
        """Test patient data change decorator denies unauthorized users"""
        @patient_data_change_required
        def test_view(request, patient_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.nurse

        with patch('apps.core.permissions.decorators.can_change_patient_personal_data', return_value=False):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_patient = Mock()
                mock_get.return_value = mock_patient

                response = test_view(request, patient_id='123')
                self.assertIsInstance(response, HttpResponseForbidden)

    def test_can_delete_event_required_decorator_allowed(self):
        """Test can delete event decorator allows authorized users"""
        @can_delete_event_required
        def test_view(request, event_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.doctor

        with patch('apps.core.permissions.decorators.can_delete_event', return_value=True):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_event = Mock()
                mock_get.return_value = mock_event

                response = test_view(request, event_id='123')
                self.assertEqual(response.status_code, 200)

    def test_can_delete_event_required_decorator_denied(self):
        """Test can delete event decorator denies unauthorized users"""
        @can_delete_event_required
        def test_view(request, event_id):
            return Mock(status_code=200)

        request = self.factory.get('/test/')
        request.user = self.nurse

        with patch('apps.core.permissions.decorators.can_delete_event', return_value=False):
            with patch('apps.core.permissions.decorators.get_object_or_404') as mock_get:
                mock_event = Mock()
                mock_get.return_value = mock_event

                response = test_view(request, event_id='123')
                self.assertIsInstance(response, HttpResponseForbidden)