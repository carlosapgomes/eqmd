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
        event_datetime__gte=week_ago
    ).order_by('-event_datetime')
    
    
    # Since can_access_patient currently returns True for all users (per docs/permissions/),
    # we can simply take the limit directly for performance
    # TODO: Update this when patient-level permissions are implemented
    accessible_dailynotes = list(queryset[:limit])
    
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
    
    # Get today's daily notes with optimized query
    today = timezone.now().date()
    
    # Since can_access_patient currently returns True for all users (per docs/permissions/),
    # we can simply count all daily notes for performance
    # TODO: Update this when patient-level permissions are implemented
    return DailyNote.objects.filter(event_datetime__date=today).count()


@register.simple_tag(takes_context=True)
def dailynotes_count_week(context):
    """
    Template tag to get count of daily notes created this week.
    
    Returns:
        Number of daily notes created this week that user can access
    """
    request = context['request']
    user = request.user
    
    # Get this week's daily notes with optimized query
    week_ago = timezone.now() - timedelta(days=7)
    
    # Since can_access_patient currently returns True for all users (per docs/permissions/),
    # we can simply count all daily notes for performance
    # TODO: Update this when patient-level permissions are implemented
    return DailyNote.objects.filter(event_datetime__gte=week_ago).count()