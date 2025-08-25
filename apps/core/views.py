from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from django.conf import settings
from apps.patients.models import Patient

def landing_page(request):
    """
    Renders the landing page for EquipeMed.
    """
    context = {
        'page_title': 'Bem-vindo ao EquipeMed',
    }
    return render(request, 'core/landing_page.html', context)

def manifest_json(request):
    """Serve dynamic PWA manifest with subtle hospital customization"""
    hospital_config = getattr(settings, 'HOSPITAL_CONFIG', {})
    short_id = hospital_config.get('short_identifier', '').lower()
    
    # Generate PWA short name
    if short_id:
        short_name = f"{short_id.capitalize()}Eqmd"
        name = f"EquipeMed - {hospital_config.get('name', 'Plataforma Médica')}"
    else:
        short_name = "EquipeMed"
        name = "EquipeMed - Plataforma Médica"
    
    manifest = {
        "name": name,
        "short_name": short_name,
        "description": "Plataforma de colaboração médica para rastreamento de pacientes e gestão hospitalar",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#2E5BBA",  # Keep EquipeMed theme color
        "orientation": "portrait-primary",
        "scope": "/",
        "categories": ["medical", "health", "productivity"],
        "lang": "pt-BR",
        "icons": [
            {
                "src": "/static/images/pwa/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-72x72-maskable.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-96x96-maskable.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-128x128-maskable.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-144x144-maskable.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-152x152-maskable.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-192x192-maskable.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-384x384-maskable.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/images/pwa/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/images/pwa/icon-512x512-maskable.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable"
            }
        ]
    }
    
    return JsonResponse(manifest)

@login_required
def dashboard_view(request):
    """
    Renders the main dashboard page for authenticated users.
    """
    from apps.core.utils.cache import get_cached_dashboard_stats
    
    # Get patient statistics for dashboard
    context = {
        'page_title': 'Painel Principal',
    }
    
    # Only show stats if user has permission to view patients
    if request.user.has_perm('patients.view_patient'):
        try:
            # Get cached dashboard data
            dashboard_data = get_cached_dashboard_stats()
            
            if dashboard_data['from_cache']:
                # Use cached data
                stats = dashboard_data['stats']
                context.update({
                    'total_patients': stats['total_patients'],
                    'inpatient_count': stats['inpatients'],
                    'outpatient_count': stats['outpatients'],
                    'recent_patients': dashboard_data['recent_patients'][:5],  # Show only 5 in dashboard
                    'cache_used': True,
                })
            else:
                # Show updating message
                context.update({
                    'total_patients': '...',
                    'inpatient_count': '...',
                    'outpatient_count': '...',
                    'recent_patients': [],
                    'updating': dashboard_data['updating'],
                    'cache_used': False,
                })
        except Exception as e:
            # Handle case where cache isn't available
            context.update({
                'total_patients': 'N/A',
                'inpatient_count': 'N/A',
                'outpatient_count': 'N/A',
                'recent_patients': [],
                'cache_error': True,
            })
    
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


class PatientHistoryView(LoginRequiredMixin, ListView):
    """View patient change history."""
    template_name = 'patients/patient_history.html'
    context_object_name = 'history'
    paginate_by = 50
    
    def get_queryset(self):
        patient_id = self.kwargs['patient_id']
        return Patient.history.filter(id=patient_id).select_related('history_user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = get_object_or_404(Patient, id=self.kwargs['patient_id'])
        return context


def health_check(request):
    """Simple health check endpoint for Docker health checks."""
    return HttpResponse("OK", content_type="text/plain")
