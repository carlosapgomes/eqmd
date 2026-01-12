import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from apps.botauth.models import MatrixUserBinding, MatrixBindingAuditLog
from apps.botauth.services import MatrixBindingService

User = get_user_model()


class MatrixUserBindingModelTest(TestCase):
    """Tests for MatrixUserBinding model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
    
    def test_create_binding(self):
        """Test creating a binding."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        self.assertFalse(binding.verified)
        self.assertFalse(binding.is_valid_for_delegation())
    
    def test_verify_binding(self):
        """Test verifying a binding."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        binding.verify()
        self.assertTrue(binding.verified)
        self.assertTrue(binding.is_valid_for_delegation())
    
    def test_inactive_user_invalid_for_delegation(self):
        """Test that inactive user binding is invalid."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br',
            verified=True
        )
        self.user.is_active = False
        self.user.save()
        self.assertFalse(binding.is_valid_for_delegation())
    
    def test_get_user_for_matrix_id(self):
        """Test looking up user by Matrix ID."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br',
            verified=True
        )
        
        found_user = MatrixUserBinding.get_user_for_matrix_id(
            '@doctor:matrix.hospital.br'
        )
        self.assertEqual(found_user, self.user)
        
        # Unverified binding should not return user
        binding.verified = False
        binding.save()
        self.assertIsNone(
            MatrixUserBinding.get_user_for_matrix_id('@doctor:matrix.hospital.br')
        )


class MatrixBindingServiceTest(TestCase):
    """Tests for MatrixBindingService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_create_binding_service(self):
        """Test creating binding via service."""
        binding, created = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        self.assertTrue(created)
        self.assertFalse(binding.verified)
        self.assertTrue(binding.verification_token)
        
        # Check audit log
        log = MatrixBindingAuditLog.objects.filter(
            matrix_id='@doctor:matrix.hospital.br'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.event_type, 'created')
    
    def test_verify_binding_service(self):
        """Test verifying binding via service."""
        binding, _ = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        token = binding.verification_token
        
        verified_binding = MatrixBindingService.verify_binding(token)
        self.assertTrue(verified_binding.verified)
        
        # Check audit log
        logs = MatrixBindingAuditLog.objects.filter(
            matrix_id='@doctor:matrix.hospital.br'
        ).order_by('created_at')
        self.assertEqual(logs.count(), 2)
        self.assertEqual(logs[1].event_type, 'verified')
    
    def test_duplicate_matrix_id_rejected(self):
        """Test that duplicate Matrix IDs are rejected."""
        MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        
        user2 = User.objects.create_user(
            username='testdoctor2',
            email='doctor2@hospital.com',
            password='testpass123'
        )
        
        with self.assertRaises(ValueError):
            MatrixBindingService.create_binding(
                user=user2,
                matrix_id='@doctor:matrix.hospital.br'
            )
    
    def test_revoke_binding_service(self):
        """Test revoking binding via service."""
        binding, _ = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        
        MatrixBindingService.revoke_binding(
            binding,
            reason='Test revocation'
        )
        
        # Binding should be deleted
        self.assertFalse(
            MatrixUserBinding.objects.filter(
                matrix_id='@doctor:matrix.hospital.br'
            ).exists()
        )
        
        # Audit log should exist
        log = MatrixBindingAuditLog.objects.filter(
            event_type='revoked'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.event_details['reason'], 'Test revocation')
    
    def test_set_delegation_enabled_service(self):
        """Test enabling/disabling delegation via service."""
        binding, _ = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        
        # Disable delegation
        MatrixBindingService.set_delegation_enabled(binding, False)
        binding.refresh_from_db()
        self.assertFalse(binding.delegation_enabled)
        
        # Enable delegation
        MatrixBindingService.set_delegation_enabled(binding, True)
        binding.refresh_from_db()
        self.assertTrue(binding.delegation_enabled)
        
        # Check audit logs
        logs = MatrixBindingAuditLog.objects.filter(
            matrix_id='@doctor:matrix.hospital.br'
        ).order_by('created_at')
        # Should have: created, delegation_disabled, delegation_enabled
        self.assertEqual(logs.count(), 3)
        self.assertEqual(logs[1].event_type, 'delegation_disabled')
        self.assertEqual(logs[2].event_type, 'delegation_enabled')


class MatrixBindingAuditLogTest(TestCase):
    """Tests for MatrixBindingAuditLog model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
    
    def test_audit_log_created_on_binding_creation(self):
        """Test that audit log is created when binding is created."""
        MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        
        log = MatrixBindingAuditLog.objects.filter(
            event_type='created'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.matrix_id, '@doctor:matrix.hospital.br')
        self.assertEqual(log.user_email, 'doctor@hospital.com')
    
    def test_audit_log_created_on_binding_verification(self):
        """Test that audit log is created when binding is verified."""
        binding, _ = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        token = binding.verification_token
        
        MatrixBindingService.verify_binding(token)
        
        log = MatrixBindingAuditLog.objects.filter(
            event_type='verified'
        ).first()
        self.assertIsNotNone(log)
    
    def test_audit_log_created_on_failed_verification(self):
        """Test that audit log is created on failed verification."""
        with self.assertRaises(ValueError):
            MatrixBindingService.verify_binding('invalid_token')
        
        log = MatrixBindingAuditLog.objects.filter(
            event_type='verification_failed'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.matrix_id, 'unknown')
        self.assertEqual(log.user_email, 'unknown')
    
    def test_audit_log_immutability(self):
        """Test that audit logs are immutable through admin."""
        from django.contrib.admin.sites import site
        
        # Check that audit log admin is registered
        self.assertIn(MatrixBindingAuditLog, site._registry)
        
        # Check that the admin has restricted permissions
        admin_class = site._registry[MatrixBindingAuditLog]
        self.assertFalse(admin_class.has_add_permission(None))
        self.assertFalse(admin_class.has_change_permission(None))
        self.assertFalse(admin_class.has_delete_permission(None))