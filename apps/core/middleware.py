from .history import get_client_ip


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