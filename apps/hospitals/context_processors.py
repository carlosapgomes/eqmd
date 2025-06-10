from .middleware import HospitalContextMiddleware


def hospital_context(request):
    """
    Context processor to add hospital context data to all templates.
    
    Makes available:
    - current_hospital: The user's current hospital or None
    - available_hospitals: QuerySet of hospitals the user can access
    - has_hospital_context: Boolean indicating if user has a hospital selected
    """
    if not request.user.is_authenticated:
        return {
            'current_hospital': None,
            'available_hospitals': [],
            'has_hospital_context': False,
        }
    
    # Get current hospital (set by middleware)
    current_hospital = getattr(request.user, 'current_hospital', None)
    has_hospital_context = getattr(request.user, 'has_hospital_context', False)
    
    # Get available hospitals for this user
    available_hospitals = HospitalContextMiddleware.get_available_hospitals(request.user)
    
    return {
        'current_hospital': current_hospital,
        'available_hospitals': available_hospitals,
        'has_hospital_context': has_hospital_context,
    }