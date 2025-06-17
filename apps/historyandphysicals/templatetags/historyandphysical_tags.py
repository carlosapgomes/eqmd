from django import template
from django.utils import timezone
from datetime import timedelta

from ..models import HistoryAndPhysical
from apps.core.permissions import can_access_patient

register = template.Library()


@register.inclusion_tag('historyandphysicals/widgets/recent_historyandphysicals.html', takes_context=True)
def recent_historyandphysicals_widget(context, limit=5):
    """
    Template tag to display recent history and physicals widget.
    
    Args:
        context: Template context containing request and user
        limit: Number of recent history and physicals to display (default: 5)
    
    Returns:
        Context dict with recent history and physicals
    """
    request = context['request']
    user = request.user
    
    # Get recent history and physicals from the last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    queryset = HistoryAndPhysical.objects.select_related('patient', 'created_by').filter(
        created_at__gte=week_ago
    ).order_by('-created_at')
    
    # Filter by hospital context if available
    if hasattr(user, 'current_hospital') and user.current_hospital:
        queryset = queryset.filter(patient__current_hospital=user.current_hospital)
    
    # Filter based on patient access permissions
    accessible_historyandphysicals = []
    for historyandphysical in queryset[:limit * 2]:  # Get more to account for filtering
        if can_access_patient(user, historyandphysical.patient):
            accessible_historyandphysicals.append(historyandphysical)
            if len(accessible_historyandphysicals) >= limit:
                break
    
    return {
        'recent_historyandphysicals': accessible_historyandphysicals,
        'request': request,
        'user': user,
    }


@register.simple_tag(takes_context=True)
def historyandphysicals_count_today(context):
    """
    Template tag to get count of history and physicals created today.
    
    Returns:
        Number of history and physicals created today that user can access
    """
    request = context['request']
    user = request.user
    
    # Get today's history and physicals
    today = timezone.now().date()
    queryset = HistoryAndPhysical.objects.filter(
        created_at__date=today
    )
    
    # Filter by hospital context if available
    if hasattr(user, 'current_hospital') and user.current_hospital:
        queryset = queryset.filter(patient__current_hospital=user.current_hospital)
    
    # Count accessible history and physicals
    count = 0
    for historyandphysical in queryset:
        if can_access_patient(user, historyandphysical.patient):
            count += 1
    
    return count


@register.simple_tag(takes_context=True)
def historyandphysicals_count_week(context):
    """
    Template tag to get count of history and physicals created this week.
    
    Returns:
        Number of history and physicals created this week that user can access
    """
    request = context['request']
    user = request.user
    
    # Get this week's history and physicals
    week_ago = timezone.now() - timedelta(days=7)
    queryset = HistoryAndPhysical.objects.filter(
        created_at__gte=week_ago
    )
    
    # Filter by hospital context if available
    if hasattr(user, 'current_hospital') and user.current_hospital:
        queryset = queryset.filter(patient__current_hospital=user.current_hospital)
    
    # Count accessible history and physicals
    count = 0
    for historyandphysical in queryset:
        if can_access_patient(user, historyandphysical.patient):
            count += 1
    
    return count