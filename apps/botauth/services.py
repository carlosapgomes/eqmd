"""
Services for Matrix user binding operations.
"""

import logging
from django.db import transaction
from django.utils import timezone

from .models import MatrixUserBinding, MatrixBindingAuditLog

logger = logging.getLogger('security.matrix_binding')


class MatrixBindingService:
    """Service for managing Matrix ↔ EQMD user bindings."""
    
    @classmethod
    @transaction.atomic
    def create_binding(cls, user, matrix_id, request=None):
        """
        Create a new Matrix binding for a user.
        Returns (binding, created) tuple.
        """
        # Check if user already has a binding
        existing = MatrixUserBinding.objects.filter(user=user).first()
        if existing:
            return existing, False
        
        # Check if matrix_id is already bound
        if MatrixUserBinding.objects.filter(matrix_id=matrix_id).exists():
            raise ValueError(f"Matrix ID {matrix_id} is already bound to another user")
        
        # Create binding
        binding = MatrixUserBinding.objects.create(
            user=user,
            matrix_id=matrix_id,
            verified=False
        )
        
        # Generate verification token
        binding.generate_verification_token()
        
        # Audit log
        cls._log_event(
            binding=binding,
            event_type=MatrixBindingAuditLog.EventType.BINDING_CREATED,
            request=request
        )
        
        logger.info(f"Matrix binding created: {user.email} ↔ {matrix_id}")
        
        return binding, True
    
    @classmethod
    def verify_binding(cls, binding_or_token, request=None):
        """
        Verify a Matrix binding using the binding object or verification token.
        """
        if isinstance(binding_or_token, str):
            # It's a token
            try:
                binding = MatrixUserBinding.objects.get(
                    verification_token=binding_or_token,
                    verification_token_expires__gt=timezone.now()
                )
            except MatrixUserBinding.DoesNotExist:
                # Log failed verification outside of transaction
                cls._log_verification_failed(binding_or_token, request)
                raise ValueError("Invalid or expired verification token")
        else:
            binding = binding_or_token
        
        # Use atomic for successful verification
        with transaction.atomic():
            binding.verify()
            
            # Audit log
            cls._log_event(
                binding=binding,
                event_type=MatrixBindingAuditLog.EventType.BINDING_VERIFIED,
                request=request
            )
            
            logger.info(f"Matrix binding verified: {binding.user.email} ↔ {binding.matrix_id}")
        
        return binding
    
    @classmethod
    @transaction.atomic
    def revoke_binding(cls, binding, request=None, reason=''):
        """
        Revoke a Matrix binding.
        """
        matrix_id = binding.matrix_id
        user_email = binding.user.email
        
        # Audit log before deletion
        cls._log_event(
            binding=binding,
            event_type=MatrixBindingAuditLog.EventType.BINDING_REVOKED,
            request=request,
            details={'reason': reason}
        )
        
        binding.delete()
        
        logger.info(f"Matrix binding revoked: {user_email} ↔ {matrix_id}")
    
    @classmethod
    @transaction.atomic
    def set_delegation_enabled(cls, binding, enabled, request=None):
        """
        Enable or disable delegation for a binding.
        """
        binding.delegation_enabled = enabled
        binding.save(update_fields=['delegation_enabled', 'updated_at'])
        
        event_type = (
            MatrixBindingAuditLog.EventType.DELEGATION_ENABLED 
            if enabled else 
            MatrixBindingAuditLog.EventType.DELEGATION_DISABLED
        )
        
        cls._log_event(
            binding=binding,
            event_type=event_type,
            request=request
        )
        
        logger.info(
            f"Matrix binding delegation {'enabled' if enabled else 'disabled'}: "
            f"{binding.user.email} ↔ {binding.matrix_id}"
        )
    
    @classmethod
    def _log_event(cls, binding, event_type, request=None, details=None):
        """Create an audit log entry."""
        MatrixBindingAuditLog.objects.create(
            binding=binding,
            matrix_id=binding.matrix_id,
            user_email=binding.user.email,
            event_type=event_type,
            event_details=details or {},
            ip_address=cls._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    
    @classmethod
    def _log_verification_failed(cls, token, request=None):
        """Log a failed verification attempt."""
        MatrixBindingAuditLog.objects.create(
            binding=None,
            matrix_id='unknown',
            user_email='unknown',
            event_type=MatrixBindingAuditLog.EventType.VERIFICATION_FAILED,
            event_details={'token_prefix': token[:8] + '...' if token else ''},
            ip_address=cls._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')