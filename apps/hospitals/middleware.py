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
        
        # Add hospital context attributes to user
        if hospital_id:
            try:
                request.user.current_hospital = Hospital.objects.get(pk=hospital_id)
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
            Hospital object if successful, None if not found
        """
        try:
            hospital = Hospital.objects.get(pk=hospital_id)
            request.session['current_hospital_id'] = str(hospital_id)
            request.user.current_hospital = hospital
            request.user.has_hospital_context = True
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
        
        For now, returns all hospitals. This can be extended later
        to implement user-specific hospital restrictions.
        
        Args:
            user: User object
            
        Returns:
            QuerySet of available hospitals
        """
        return Hospital.objects.all()