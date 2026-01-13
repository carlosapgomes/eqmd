import logging
import time

logger = logging.getLogger('security.delegation')

class DelegatedRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        
        if getattr(request, 'is_delegated', False):
            duration = time.time() - start_time
            logger.info(
                f"DELEGATED: {request.method} {request.path} "
                f"user={request.user.email} bot={request.actor_name} "
                f"status={response.status_code} duration={duration:.3f}s"
            )
        
        return response