from simple_history.models import HistoricalRecords
from django.db import models
from django.conf import settings


class AuditHistoricalRecords(HistoricalRecords):
    """Custom historical records with enhanced audit capabilities."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('cascade_delete_history', False)
        kwargs.setdefault('history_change_reason_field', models.TextField(null=True))
        super().__init__(*args, **kwargs)


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip