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