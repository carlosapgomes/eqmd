from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import JsonResponse
from apps.hospitals.models import Hospital
from apps.hospitals.context_processors import hospital_context
from apps.hospitals.views import hospital_context_switch_ajax

User = get_user_model()


class HospitalContextNavbarTest(TestCase):
    """Test hospital context navbar functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="testpass123"
        )
        self.hospital1 = Hospital.objects.create(
            name="Hospital A",
            short_name="HA",
            city="City A"
        )
        self.hospital2 = Hospital.objects.create(
            name="Hospital B", 
            short_name="HB",
            city="City B"
        )
        self.user.hospitals.add(self.hospital1, self.hospital2)
    
    def test_context_processor_provides_hospital_data(self):
        """Test that context processor provides correct hospital data"""
        request = self.factory.get('/')
        request.user = self.user
        
        context_data = hospital_context(request)
        
        self.assertIn('current_hospital', context_data)
        self.assertIn('available_hospitals', context_data)
        self.assertIn('has_hospital_context', context_data)
        self.assertEqual(context_data['available_hospitals'].count(), 2)
    
    def test_context_processor_unauthenticated(self):
        """Test context processor with unauthenticated user"""
        request = self.factory.get('/')
        request.user = None
        
        # Mock an anonymous user
        class AnonymousUser:
            is_authenticated = False
        
        request.user = AnonymousUser()
        
        context_data = hospital_context(request)
        
        self.assertIsNone(context_data['current_hospital'])
        self.assertEqual(len(context_data['available_hospitals']), 0)
        self.assertFalse(context_data['has_hospital_context'])
    
    def test_ajax_hospital_switch_success(self):
        """Test successful AJAX hospital switching"""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('hospitals:context_switch'),
            {'hospital_id': str(self.hospital1.id)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('selecionado', data['message'])
        self.assertEqual(data['hospital']['id'], str(self.hospital1.id))
        self.assertEqual(data['hospital']['name'], self.hospital1.name)
    
    def test_ajax_hospital_switch_clear_context(self):
        """Test clearing hospital context via AJAX"""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('hospitals:context_switch'),
            {'hospital_id': ''},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('removido', data['message'])
        self.assertIsNone(data['hospital'])
    
    def test_ajax_hospital_switch_invalid_hospital(self):
        """Test AJAX switch with invalid hospital ID"""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('hospitals:context_switch'),
            {'hospital_id': 'invalid-uuid'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('não encontrado', data['message'])
    
    def test_ajax_hospital_switch_unauthorized(self):
        """Test AJAX switch with hospital user doesn't have access to"""
        other_hospital = Hospital.objects.create(
            name="Other Hospital",
            short_name="OH",
            city="Other City"
        )
        
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('hospitals:context_switch'),
            {'hospital_id': str(other_hospital.id)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('não encontrado', data['message'])