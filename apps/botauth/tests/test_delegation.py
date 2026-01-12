"""
Tests for the delegated token endpoint (Phase 06).
"""

import pytest
import jwt
import time
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.botauth.models import MatrixUserBinding, DelegationAuditLog
from apps.botauth.bot_service import BotClientService
from apps.botauth.services import MatrixBindingService
from apps.botauth.tokens import DelegatedTokenGenerator

User = get_user_model()


class DelegatedTokenEndpointTest(TestCase):
    """Tests for the delegated token endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create doctor
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        
        # Create Matrix binding
        binding, _ = MatrixBindingService.create_binding(
            user=self.doctor,
            matrix_id='@doctor:matrix.hospital.br'
        )
        MatrixBindingService.verify_binding(binding)
        
        # Create bot
        self.bot, self.bot_secret = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
    
    def test_successful_delegation(self):
        """Test successful token delegation."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertEqual(response.data['token_type'], 'Bearer')
        self.assertIn('expires_in', response.data)
        
        # Verify audit log
        log = DelegationAuditLog.objects.filter(user=self.doctor).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'issued')
        self.assertEqual(log.granted_scopes, ['patient:read'])
    
    def test_invalid_bot_credentials(self):
        """Test rejection with invalid bot credentials."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': 'wrong_secret',
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
        
        # Check audit log
        log = DelegationAuditLog.objects.filter(
            status='denied_bot'
        ).first()
        self.assertIsNotNone(log)
    
    def test_unknown_matrix_id(self):
        """Test rejection with unknown Matrix ID."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@unknown:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 403)
        
        # Check audit log
        log = DelegationAuditLog.objects.filter(
            status='denied_binding'
        ).first()
        self.assertIsNotNone(log)
    
    def test_inactive_user(self):
        """Test rejection when user is inactive."""
        self.doctor.is_active = False
        self.doctor.save()
        
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        # The binding is filtered out because user is inactive
        self.assertEqual(response.status_code, 403)
        self.assertIn('no valid user binding', response.data['error'].lower())
    
    def test_unauthorized_scope(self):
        """Test rejection when requesting unauthorized scope."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['prescription:draft']  # Bot doesn't have this
        }, format='json')
        
        self.assertEqual(response.status_code, 403)
        
        # Check audit log
        log = DelegationAuditLog.objects.filter(
            status='denied_scopes'
        ).first()
        self.assertIsNotNone(log)
    
    def test_missing_required_fields(self):
        """Test rejection with missing required fields."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing required fields', response.data['error'])
    
    def test_empty_scopes(self):
        """Test rejection with empty scopes list."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': []
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('scopes must be a non-empty list', response.data['error'])
    
    def test_token_contains_correct_claims(self):
        """Test that generated token contains all required claims."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read', 'dailynote:draft']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # Decode token
        token = response.data['access_token']
        payload = DelegatedTokenGenerator.decode_token(token)
        
        # Check required claims
        self.assertIn('iss', payload)
        self.assertIn('sub', payload)
        self.assertIn('aud', payload)
        self.assertIn('exp', payload)
        self.assertIn('iat', payload)
        self.assertIn('jti', payload)
        self.assertIn('azp', payload)
        self.assertIn('scope', payload)
        
        # Check user info
        self.assertEqual(payload['user_email'], self.doctor.email)
        self.assertEqual(payload['bot_name'], self.bot.display_name)
        
        # Check scopes
        scopes = DelegatedTokenGenerator.extract_scopes(payload)
        self.assertEqual(scopes, {'patient:read', 'dailynote:draft'})
    
    def test_multiple_scopes_request(self):
        """Test requesting multiple scopes at once."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read', 'dailynote:draft']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # Check token has both scopes
        token = response.data['access_token']
        payload = DelegatedTokenGenerator.decode_token(token)
        scopes = DelegatedTokenGenerator.extract_scopes(payload)
        self.assertEqual(scopes, {'patient:read', 'dailynote:draft'})
    
    def test_token_expiration_within_limits(self):
        """Test that token expiration is within configured limits."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # Check expiration time
        expires_in = response.data['expires_in']
        self.assertLessEqual(expires_in, 600)  # Max 10 minutes
        self.assertGreater(expires_in, 0)
    
    def test_rate_limiting_respected(self):
        """Test that rate limiting is enforced."""
        # Create a bot with low rate limit
        rate_limited_bot, secret = BotClientService.create_bot(
            display_name='Rate Limited Bot',
            allowed_scopes=['patient:read']
        )
        rate_limited_bot.max_delegations_per_hour = 2
        rate_limited_bot.save()
        
        # Make requests up to the limit
        for _ in range(2):
            response = self.client.post('/auth/api/delegated-token/', {
                'client_id': rate_limited_bot.client.client_id,
                'client_secret': secret,
                'matrix_id': '@doctor:matrix.hospital.br',
                'scopes': ['patient:read']
            }, format='json')
            self.assertEqual(response.status_code, 200)
        
        # Next request should be rate limited
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': rate_limited_bot.client.client_id,
            'client_secret': secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 429)
        self.assertIn('Rate limit', response.data['error'])


class TokenGeneratorTest(TestCase):
    """Tests for the token generator utility."""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0
        )
        
        self.bot, _ = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read']
        )
    
    def test_token_generation(self):
        """Test basic token generation."""
        token = DelegatedTokenGenerator.generate_token(
            user=self.doctor,
            bot_profile=self.bot,
            scopes=['patient:read']
        )
        
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)
    
    def test_token_decoding(self):
        """Test token decoding and validation."""
        token = DelegatedTokenGenerator.generate_token(
            user=self.doctor,
            bot_profile=self.bot,
            scopes=['patient:read']
        )
        
        payload = DelegatedTokenGenerator.decode_token(token)
        
        self.assertEqual(payload['user_email'], self.doctor.email)
        self.assertEqual(payload['bot_name'], self.bot.display_name)
        self.assertEqual(payload['azp'], self.bot.client.client_id)
    
    def test_extract_user_id(self):
        """Test extracting user ID from token."""
        token = DelegatedTokenGenerator.generate_token(
            user=self.doctor,
            bot_profile=self.bot,
            scopes=['patient:read']
        )
        
        payload = DelegatedTokenGenerator.decode_token(token)
        user_id = DelegatedTokenGenerator.extract_user_id(payload)
        
        self.assertEqual(str(user_id), str(self.doctor.id))
    
    def test_extract_scopes(self):
        """Test extracting scopes from token."""
        scopes = ['patient:read', 'dailynote:draft']
        token = DelegatedTokenGenerator.generate_token(
            user=self.doctor,
            bot_profile=self.bot,
            scopes=scopes
        )
        
        payload = DelegatedTokenGenerator.decode_token(token)
        extracted_scopes = DelegatedTokenGenerator.extract_scopes(payload)
        
        self.assertEqual(extracted_scopes, set(scopes))
    
    def test_token_expiration(self):
        """Test that tokens expire correctly."""
        token = DelegatedTokenGenerator.generate_token(
            user=self.doctor,
            bot_profile=self.bot,
            scopes=['patient:read'],
            ttl_seconds=1
        )
        
        # Token should be valid immediately
        payload = DelegatedTokenGenerator.decode_token(token)
        self.assertIsNotNone(payload)
        
        # Wait for expiration
        time.sleep(2)
        
        # Token should now be expired
        with self.assertRaises(jwt.ExpiredSignatureError):
            DelegatedTokenGenerator.decode_token(token)