from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

def landing_page(request):
    """
    Renders the landing page for EquipeMed.
    """
    context = {
        'page_title': 'Bem-vindo ao EquipeMed',
    }
    return render(request, 'core/landing_page.html', context)

@login_required
def dashboard_view(request):
    """
    Renders the main dashboard page for authenticated users.
    """
    context = {
        'page_title': 'Painel Principal',
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def permission_performance_test(request):
    """Test view for permission system performance and UI integration."""
    from apps.core.permissions import (
        get_cache_stats,
        is_caching_enabled,
    )
    from apps.core.permissions.queries import get_permission_summary_optimized

    context = {
        'user': request.user,
        'caching_enabled': is_caching_enabled(),
        'cache_stats': get_cache_stats() if is_caching_enabled() else None,
        'permission_summary': get_permission_summary_optimized(request.user),
        'page_title': 'Permission Performance Test',
    }

    return render(request, 'core/permission_performance_test.html', context)


@login_required
@require_http_methods(["GET"])
def permission_performance_api(request):
    """API endpoint for permission performance data."""
    from apps.core.permissions import (
        get_cache_stats,
        is_caching_enabled,
    )
    from apps.core.permissions.queries import get_permission_summary_optimized

    data = {
        'caching_enabled': is_caching_enabled(),
        'cache_stats': get_cache_stats() if is_caching_enabled() else None,
        'permission_summary': get_permission_summary_optimized(request.user),
        'user_info': {
            'id': request.user.id,
            'email': request.user.email,
            'profession_type': getattr(request.user, 'profession_type', None),
        }
    }

    return JsonResponse(data)
