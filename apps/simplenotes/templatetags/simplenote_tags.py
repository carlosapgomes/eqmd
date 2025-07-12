from django import template
from django.utils import timezone
from datetime import timedelta

from ..models import SimpleNote
from apps.core.permissions import can_access_patient

register = template.Library()


@register.inclusion_tag('simplenotes/widgets/recent_simplenotes.html', takes_context=True)
def recent_simplenotes_widget(context, limit=5):
    """
    Template tag to display recent simple notes widget.
    
    Args:
        context: Template context containing request and user
        limit: Number of recent simple notes to display (default: 5)
    
    Returns:
        Context dict with recent simple notes
    """
    request = context['request']
    user = request.user
    
    # Get recent simple notes from the last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    queryset = SimpleNote.objects.select_related('patient', 'created_by').filter(
        created_at__gte=week_ago
    ).order_by('-created_at')
    
    
    # Filter based on patient access permissions
    accessible_simplenotes = []
    for simplenote in queryset[:limit * 2]:  # Get more to account for filtering
        if can_access_patient(user, simplenote.patient):
            accessible_simplenotes.append(simplenote)
            if len(accessible_simplenotes) >= limit:
                break
    
    return {
        'recent_simplenotes': accessible_simplenotes,
        'request': request,
        'user': user,
    }


@register.simple_tag(takes_context=True)
def simplenotes_count_today(context):
    """
    Template tag to get count of simple notes created today.
    
    Returns:
        Number of simple notes created today that user can access
    """
    request = context['request']
    user = request.user
    
    # Get today's simple notes
    today = timezone.now().date()
    queryset = SimpleNote.objects.filter(
        created_at__date=today
    )
    
    
    # Count accessible simple notes
    count = 0
    for simplenote in queryset:
        if can_access_patient(user, simplenote.patient):
            count += 1
    
    return count


@register.simple_tag(takes_context=True)
def simplenotes_count_week(context):
    """
    Template tag to get count of simple notes created this week.
    
    Returns:
        Number of simple notes created this week that user can access
    """
    request = context['request']
    user = request.user
    
    # Get this week's simple notes
    week_ago = timezone.now() - timedelta(days=7)
    queryset = SimpleNote.objects.filter(
        created_at__gte=week_ago
    )
    
    
    # Count accessible simple notes
    count = 0
    for simplenote in queryset:
        if can_access_patient(user, simplenote.patient):
            count += 1
    
    return count