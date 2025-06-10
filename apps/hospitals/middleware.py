from django.shortcuts import get_object_or_404
from apps.hospitals.models import Hospital


class HospitalContextMiddleware:
    """
    Middleware to manage hospital context for users.
    
    This middleware:
    1. Adds current hospital context to the user object
    2. Handles session management for hospital selection
    3. Provides helper methods for switching hospitals
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add hospital context to user if authenticated
        if request.user.is_authenticated:
            self._add_hospital_context(request)
        
        response = self.get_response(request)
        return response

    def _add_hospital_context(self, request):
        """Add hospital context to the user object."""
        # Get current hospital ID from session
        hospital_id = request.session.get('current_hospital_id')
        
        # If no session context, try to auto-select user's default hospital
        if not hospital_id and hasattr(request.user, 'get_default_hospital'):
            default_hospital = request.user.get_default_hospital()
            if default_hospital:
                hospital_id = str(default_hospital.id)
                request.session['current_hospital_id'] = hospital_id
                # Update last_hospital for future sessions
                if request.user.last_hospital != default_hospital:
                    request.user.last_hospital = default_hospital
                    request.user.save(update_fields=['last_hospital'])
        
        # Add hospital context attributes to user
        if hospital_id:
            try:
                hospital = Hospital.objects.get(pk=hospital_id)
                # Validate user is a member of this hospital
                if hasattr(request.user, 'is_hospital_member') and not request.user.is_hospital_member(hospital):
                    # User is not a member, clear session and try default
                    request.session.pop('current_hospital_id', None)
                    default_hospital = request.user.get_default_hospital() if hasattr(request.user, 'get_default_hospital') else None
                    if default_hospital:
                        request.user.current_hospital = default_hospital
                        request.user.has_hospital_context = True
                        request.session['current_hospital_id'] = str(default_hospital.id)
                    else:
                        request.user.current_hospital = None
                        request.user.has_hospital_context = False
                else:
                    request.user.current_hospital = hospital
                    request.user.has_hospital_context = True
            except Hospital.DoesNotExist:
                # Remove invalid hospital ID from session
                request.session.pop('current_hospital_id', None)
                request.user.current_hospital = None
                request.user.has_hospital_context = False
        else:
            request.user.current_hospital = None
            request.user.has_hospital_context = False

    @staticmethod
    def set_hospital_context(request, hospital_id):
        """
        Set the current hospital context for the user.
        
        Args:
            request: Django request object
            hospital_id: UUID of the hospital to set as current
            
        Returns:
            Hospital object if successful, None if not found or not authorized
        """
        try:
            hospital = Hospital.objects.get(pk=hospital_id)
            
            # Validate user is a member of this hospital
            if hasattr(request.user, 'is_hospital_member') and not request.user.is_hospital_member(hospital):
                return None
            
            request.session['current_hospital_id'] = str(hospital_id)
            request.user.current_hospital = hospital
            request.user.has_hospital_context = True
            
            # Update user's last_hospital for future sessions
            if hasattr(request.user, 'last_hospital') and request.user.last_hospital != hospital:
                request.user.last_hospital = hospital
                request.user.save(update_fields=['last_hospital'])
            
            return hospital
        except Hospital.DoesNotExist:
            return None

    @staticmethod
    def clear_hospital_context(request):
        """Clear the current hospital context for the user."""
        request.session.pop('current_hospital_id', None)
        if hasattr(request.user, 'current_hospital'):
            request.user.current_hospital = None
            request.user.has_hospital_context = False

    @staticmethod
    def get_available_hospitals(user):
        """
        Get available hospitals for the user.
        
        Returns only hospitals the user is a member of.
        
        Args:
            user: User object
            
        Returns:
            QuerySet of available hospitals
        """
        if not user.is_authenticated:
            return Hospital.objects.none()
        
        if hasattr(user, 'hospitals'):
            return user.hospitals.all()
        
        # Fallback for users without hospital relationships (e.g., superusers)
        if getattr(user, 'is_superuser', False):
            return Hospital.objects.all()
        
        return Hospital.objects.none()