from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _
import logging

from .history import get_client_ip

logger = logging.getLogger('security.password_change')


class EnhancedHistoryMiddleware:
    """Enhanced history middleware with IP tracking."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store IP address for history records (before processing request)
        if hasattr(request, 'user') and request.user.is_authenticated:
            request._history_ip = get_client_ip(request)
        
        response = self.get_response(request)
        return response


class PasswordChangeRequiredMiddleware:
    """
    Middleware that enforces password change for users with password_change_required=True.
    
    Integrates with existing allauth flow and hospital security requirements.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip middleware if user doesn't need password change
        if not getattr(request.user, 'password_change_required', False):
            return self.get_response(request)
        
        # Allow access to password change related URLs
        password_change_urls = [
            reverse('core:password_change_required'),
            reverse('account_change_password'),
            reverse('account_logout'),
            '/admin/logout/',  # Allow admin logout
        ]
        
        # Allow static files and media files
        if (request.path_info.startswith('/static/') or 
            request.path_info.startswith('/media/') or
            request.path_info in password_change_urls):
            return self.get_response(request)
        
        # Log security event
        logger.info(
            f'Password change required redirect for user {request.user.username} '
            f'from IP {get_client_ip(request)} '
            f'accessing {request.path_info}'
        )
        
        # Redirect to password change page
        try:
            messages.warning(
                request,
                _('Por segurança, você deve alterar sua senha antes de continuar.')
            )
        except Exception:
            # Handle case where messages framework is not properly configured
            pass
        
        return redirect('core:password_change_required')


class TermsAcceptanceRequiredMiddleware:
    """
    Middleware that enforces terms acceptance for authenticated users.
    
    Users must accept terms before accessing any protected content.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip middleware if user has already accepted terms
        if getattr(request.user, 'terms_accepted', False):
            return self.get_response(request)
        
        # Allow access to terms acceptance and logout related URLs
        terms_allowed_urls = [
            reverse('core:accept_terms'),
            reverse('core:terms_of_use'),
            reverse('account_logout'),
            '/admin/logout/',  # Allow admin logout
        ]
        
        # Also allow password change if required (password change comes first)
        if getattr(request.user, 'password_change_required', False):
            terms_allowed_urls.extend([
                reverse('core:password_change_required'),
                reverse('account_change_password'),
            ])
        
        # Allow static files and media files
        if (request.path_info.startswith('/static/') or 
            request.path_info.startswith('/media/') or
            request.path_info in terms_allowed_urls):
            return self.get_response(request)
        
        # Log security event
        logger.info(
            f'Terms acceptance required redirect for user {request.user.username} '
            f'from IP {get_client_ip(request)} '
            f'accessing {request.path_info}'
        )
        
        # Redirect to terms acceptance page
        try:
            messages.info(
                request,
                _('Você precisa aceitar os termos de uso para continuar.')
            )
        except Exception:
            # Handle case where messages framework is not properly configured
            pass
        
        return redirect('core:accept_terms')


class UserLifecycleMiddleware:
    """
    Simplified middleware that enforces essential user lifecycle rules.
    
    Checks for:
    - Account expiration
    - Administrative suspension
    - Departed user status
    
    Integrates with existing security flow (after terms, before password change).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('security.user_lifecycle')
    
    def __call__(self, request):
        # Skip middleware for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip middleware for superusers (admin access)
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Update simple activity tracking
        self._update_user_activity(request)
        
        # Check lifecycle status and enforce restrictions
        lifecycle_response = self._check_lifecycle_status(request)
        if lifecycle_response:
            return lifecycle_response
        
        return self.get_response(request)
    
    def _update_user_activity(self, request):
        """Update simple user activity tracking"""
        user = request.user
        
        # Only update for meaningful activities (not static files, etc.)
        if self._is_meaningful_activity(request):
            user.update_activity_timestamp()
            
            # Update status if user was previously inactive
            if user.account_status == 'inactive':
                user.account_status = 'active'
                user._change_reason = 'User reactivated due to activity'
                user.save(update_fields=['account_status', 'last_meaningful_activity'])
            else:
                user.save(update_fields=['last_meaningful_activity'])
    
    def _is_meaningful_activity(self, request):
        """Determine if request represents meaningful user activity"""
        # Skip static files and basic endpoints
        if (request.path_info.startswith('/static/') or 
            request.path_info.startswith('/media/') or
            request.path_info in ['/health/', '/manifest.json']):
            return False
        
        # Skip AJAX polling requests
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            if request.path_info.endswith('/status/') or 'poll' in request.path_info:
                return False
        
        return True
    
    def _check_lifecycle_status(self, request):
        """Check user lifecycle status and return appropriate response"""
        user = request.user
        
        # Update user status if needed (simplified)
        self._update_user_status(user)
        
        # Check for blocking conditions
        if user.is_expired:
            return self._handle_expired_user(request, user)
        
        if user.account_status == 'suspended':
            return self._handle_suspended_user(request, user)
        
        if user.account_status == 'departed':
            return self._handle_departed_user(request, user)
        
        if user.account_status == 'renewal_required':
            return self._handle_renewal_required(request, user)
        
        # Allow lifecycle management URLs
        lifecycle_urls = [
            reverse('core:account_expired'),
            reverse('core:account_suspended'), 
            reverse('core:account_renewal_required'),
            reverse('account_logout'),
            '/admin/logout/',
        ]
        
        if request.path_info in lifecycle_urls:
            return None
        
        # No blocking conditions - allow access
        return None
    
    def _update_user_status(self, user):
        """Update user status based on current conditions (simplified)"""
        old_status = user.account_status
        new_status = None
        
        # Simple status updates based on expiration only
        if user.is_expired and user.account_status != 'expired':
            new_status = 'expired'
        elif user.is_expiring_soon and user.account_status == 'active':
            new_status = 'expiring_soon'
        elif user.is_inactive and user.account_status in ['active', 'expiring_soon']:
            new_status = 'inactive'
        
        # Update status if changed
        if new_status and new_status != old_status:
            user.account_status = new_status
            user._change_reason = f'Status auto-updated from {old_status} to {new_status}'
            user.save(update_fields=['account_status'])
            
            # Log status change
            self.logger.info(
                f'User lifecycle status updated: {user.username} '
                f'from {old_status} to {new_status}'
            )
    
    def _handle_expired_user(self, request, user):
        """Handle expired user access attempt"""
        self.logger.warning(
            f'Expired user access attempt: {user.username} '
            f'(expired: {user.access_expires_at}) '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                f'Sua conta expirou em {user.access_expires_at.strftime("%d/%m/%Y")}. '
                'Entre em contato com o administrador para renovar o acesso.'
            )
        except Exception:
            pass
        
        return redirect('core:account_expired')
    
    def _handle_suspended_user(self, request, user):
        """Handle suspended user access attempt"""
        self.logger.warning(
            f'Suspended user access attempt: {user.username} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                'Sua conta foi suspensa. Entre em contato com o administrador.'
            )
        except Exception:
            pass
        
        return redirect('core:account_suspended')
    
    def _handle_departed_user(self, request, user):
        """Handle departed user access attempt"""
        self.logger.error(
            f'Departed user access attempt: {user.username} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                'Esta conta foi desativada permanentemente.'
            )
        except Exception:
            pass
        
        return redirect('core:account_departed')
    
    def _handle_renewal_required(self, request, user):
        """Handle user requiring access renewal"""
        self.logger.info(
            f'User requiring renewal: {user.username} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.warning(
                request,
                'Seu acesso requer renovação. Confirme suas informações para continuar.'
            )
        except Exception:
            pass
        
        return redirect('core:account_renewal_required')