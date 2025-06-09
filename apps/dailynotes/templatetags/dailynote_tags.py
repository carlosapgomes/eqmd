from django import template
from django.utils import timezone
from datetime import timedelta

from ..models import DailyNote
from apps.core.permissions import can_access_patient

register = template.Library()


@register.inclusion_tag('dailynotes/widgets/recent_dailynotes.html', takes_context=True)
def recent_dailynotes_widget(context, limit=5):
    """
    Template tag to display recent daily notes widget.
    
    Args:
        context: Template context containing request and user
        limit: Number of recent daily notes to display (default: 5)
    
    Returns:
        Context dict with recent daily notes
    """
    request = context['request']
    user = request.user
    
    # Get recent daily notes from the last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    queryset = DailyNote.objects.select_related('patient', 'created_by').filter(
        created_at__gte=week_ago
    ).order_by('-created_at')
    
    # Filter by hospital context if available
    if hasattr(user, 'current_hospital') and user.current_hospital:
        queryset = queryset.filter(patient__current_hospital=user.current_hospital)
    
    # Filter based on patient access permissions
    accessible_dailynotes = []
    for dailynote in queryset[:limit * 2]:  # Get more to account for filtering
        if can_access_patient(user, dailynote.patient):
            accessible_dailynotes.append(dailynote)
            if len(accessible_dailynotes) >= limit:
                break
    
    return {
        'recent_dailynotes': accessible_dailynotes,
        'request': request,
        'user': user,
    }


@register.simple_tag(takes_context=True)
def dailynotes_count_today(context):
    """
    Template tag to get count of daily notes created today.
    
    Returns:
        Number of daily notes created today that user can access
    """
    request = context['request']
    user = request.user
    
    # Get today's daily notes
    today = timezone.now().date()
    queryset = DailyNote.objects.filter(
        created_at__date=today
    )
    
    # Filter by hospital context if available
    if hasattr(user, 'current_hospital') and user.current_hospital:
        queryset = queryset.filter(patient__current_hospital=user.current_hospital)
    
    # Count accessible daily notes
    count = 0
    for dailynote in queryset:
        if can_access_patient(user, dailynote.patient):
            count += 1
    
    return count


@register.simple_tag(takes_context=True)
def dailynotes_count_week(context):
    """
    Template tag to get count of daily notes created this week.
    
    Returns:
        Number of daily notes created this week that user can access
    """
    request = context['request']
    user = request.user
    
    # Get this week's daily notes
    week_ago = timezone.now() - timedelta(days=7)
    queryset = DailyNote.objects.filter(
        created_at__gte=week_ago
    )
    
    # Filter by hospital context if available
    if hasattr(user, 'current_hospital') and user.current_hospital:
        queryset = queryset.filter(patient__current_hospital=user.current_hospital)
    
    # Count accessible daily notes
    count = 0
    for dailynote in queryset:
        if can_access_patient(user, dailynote.patient):
            count += 1
    
    return count