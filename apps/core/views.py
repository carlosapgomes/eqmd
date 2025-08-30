from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, TemplateView
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlparse
from django.utils import timezone
import logging
from datetime import datetime
from apps.patients.models import Patient
from allauth.account.views import PasswordChangeView

logger = logging.getLogger(__name__)


def landing_page(request):
    """
    Renders the landing page for EquipeMed.
    """
    context = {
        "page_title": "Bem-vindo ao EquipeMed",
    }
    return render(request, "core/landing_page.html", context)


def terms_of_use(request):
    """
    Renders the terms of use page for the medical platform.
    """
    # Determine the appropriate return URL
    referer = request.META.get("HTTP_REFERER", "")
    if "accept-terms" in referer:
        return_url = reverse("core:accept_terms")
    else:
        return_url = reverse("account_login")

    context = {
        "page_title": "Termos de Uso",
        "last_updated": datetime(2025, 8, 30),  # Update this when terms change
        "return_url": return_url,
    }
    return render(request, "core/terms_of_use.html", context)


@login_required
def accept_terms(request):
    """
    Handles terms acceptance for authenticated users.

    GET: Shows the terms acceptance page
    POST: Records the terms acceptance and redirects to dashboard
    """
    if request.method == "POST":
        # Record terms acceptance
        request.user.terms_accepted = True
        request.user.terms_accepted_at = timezone.now()
        request.user._change_reason = "Terms of use accepted"
        request.user.save(update_fields=["terms_accepted", "terms_accepted_at"])

        # Log the acceptance for security audit
        from .history import get_client_ip

        logger.info(
            f"Terms accepted by user {request.user.username} "
            f"from IP {get_client_ip(request)} "
            f"at {timezone.now()}"
        )

        # Success message
        messages.success(
            request, _("Termos de uso aceitos com sucesso! Bem-vindo ao sistema.")
        )

        # Redirect to dashboard or intended destination
        next_url = request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect("core:dashboard")

    # GET request - show terms acceptance form
    context = {
        "page_title": "Aceitar Termos de Uso",
        "last_updated": datetime(2025, 8, 30),  # Update this when terms change
    }
    return render(request, "core/accept_terms.html", context)


def manifest_json(request):
    """Serve dynamic PWA manifest with subtle hospital customization"""
    hospital_config = getattr(settings, "HOSPITAL_CONFIG", {})
    short_id = hospital_config.get("short_identifier", "").lower()

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
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-72x72-maskable.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-96x96-maskable.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-128x128-maskable.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-144x144-maskable.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-152x152-maskable.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-192x192-maskable.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-384x384-maskable.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/static/images/pwa/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/pwa/icon-512x512-maskable.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
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
        "page_title": "Painel Principal",
    }

    # Only show stats if user has permission to view patients
    if request.user.has_perm("patients.view_patient"):
        try:
            # Get cached dashboard data
            dashboard_data = get_cached_dashboard_stats()

            if dashboard_data["from_cache"]:
                # Use cached data
                stats = dashboard_data["stats"]
                context.update(
                    {
                        "total_patients": stats["total_patients"],
                        "inpatient_count": stats["inpatients"],
                        "outpatient_count": stats["outpatients"],
                        "recent_patients": dashboard_data["recent_patients"][
                            :5
                        ],  # Show only 5 in dashboard
                        "cache_used": True,
                    }
                )
            else:
                # Show updating message
                context.update(
                    {
                        "total_patients": "...",
                        "inpatient_count": "...",
                        "outpatient_count": "...",
                        "recent_patients": [],
                        "updating": dashboard_data["updating"],
                        "cache_used": False,
                    }
                )
        except Exception as e:
            # Handle case where cache isn't available
            context.update(
                {
                    "total_patients": "N/A",
                    "inpatient_count": "N/A",
                    "outpatient_count": "N/A",
                    "recent_patients": [],
                    "cache_error": True,
                }
            )

    return render(request, "core/dashboard.html", context)


@login_required
def permission_performance_test(request):
    """Test view for permission system performance and UI integration."""
    from apps.core.permissions import (
        get_cache_stats,
        is_caching_enabled,
    )
    from apps.core.permissions.queries import get_permission_summary_optimized

    context = {
        "user": request.user,
        "caching_enabled": is_caching_enabled(),
        "cache_stats": get_cache_stats() if is_caching_enabled() else None,
        "permission_summary": get_permission_summary_optimized(request.user),
        "page_title": "Permission Performance Test",
    }

    return render(request, "core/permission_performance_test.html", context)


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
        "caching_enabled": is_caching_enabled(),
        "cache_stats": get_cache_stats() if is_caching_enabled() else None,
        "permission_summary": get_permission_summary_optimized(request.user),
        "user_info": {
            "id": request.user.id,
            "email": request.user.email,
            "profession_type": getattr(request.user, "profession_type", None),
        },
    }

    return JsonResponse(data)


class PatientHistoryView(LoginRequiredMixin, ListView):
    """View patient change history."""

    template_name = "patients/patient_history.html"
    context_object_name = "history"
    paginate_by = 50

    def get_queryset(self):
        patient_id = self.kwargs["patient_id"]
        return Patient.history.filter(id=patient_id).select_related("history_user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient"] = get_object_or_404(Patient, id=self.kwargs["patient_id"])
        return context


def health_check(request):
    """Simple health check endpoint for Docker health checks."""
    return HttpResponse("OK", content_type="text/plain")


def custom_permission_denied_view(request, exception):
    """Custom 403 error handler with medical theme styling."""
    logger.warning(
        f"Permission denied for user {request.user} accessing {request.path}"
    )

    # Determine safe return URL
    return_url = get_safe_return_url(request)

    context = {
        "return_url": return_url,
        "page_title": "Acesso Negado - EquipeMed",
    }

    return render(request, "403.html", context, status=403)


def custom_page_not_found_view(request, exception):
    """Custom 404 error handler with medical theme styling."""
    logger.info(f"Page not found: {request.path} for user {request.user}")

    # Determine safe return URL
    return_url = get_safe_return_url(request)

    context = {
        "return_url": return_url,
        "page_title": "Página Não Encontrada - EquipeMed",
    }

    return render(request, "404.html", context, status=404)


def custom_server_error_view(request):
    """Custom 500 error handler with medical theme styling."""
    logger.error(
        f"Server error for user {request.user if hasattr(request, 'user') else 'Unknown'} accessing {request.path}"
    )

    # Minimal context for server errors (no dynamic content)
    context = {
        "page_title": "Erro do Servidor - EquipeMed",
    }

    return render(request, "500.html", context, status=500)


def get_safe_return_url(request):
    """
    Determine a safe return URL for error pages.
    Priority: safe referer → dashboard → login → landing page
    """
    # Check HTTP_REFERER for safe same-domain URLs
    referer = request.META.get("HTTP_REFERER")
    if referer:
        try:
            referer_parsed = urlparse(referer)
            request_parsed = urlparse(request.build_absolute_uri())

            # Only use referer if it's from the same domain
            if referer_parsed.netloc == request_parsed.netloc:
                return referer
        except Exception:
            pass  # Invalid referer, continue to fallbacks

    # Fallback hierarchy based on authentication
    try:
        if hasattr(request, "user") and request.user.is_authenticated:
            return reverse("core:dashboard")
        else:
            return reverse("account_login")
    except Exception:
        # Final fallback if URL reversal fails
        return reverse("core:landing_page")


class SignupBlockedView(TemplateView):
    """
    Custom view that blocks all signup attempts with professional medical messaging.
    Returns 403 Forbidden status and renders a professional error page.
    """

    template_name = "account/signup.html"

    def dispatch(self, request, *args, **kwargs):
        """Log signup attempt and return 403 status."""
        logger.warning(
            f"Signup attempt blocked for IP {request.META.get('REMOTE_ADDR')} accessing {request.path}"
        )

        # Set 403 status for all methods (GET, POST, etc.)
        response = super().dispatch(request, *args, **kwargs)
        response.status_code = 403
        return response

    def get_context_data(self, **kwargs):
        """Add context for the signup blocked template."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Registro Fechado - EquipeMed",
                "return_url": get_safe_return_url(self.request),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class PasswordChangeRequiredView(PasswordChangeView):
    """
    Custom password change view that clears the password_change_required flag.

    Extends allauth's PasswordChangeView to integrate with our security flow.
    """

    template_name = "core/password_change_required.html"
    success_url = reverse_lazy("core:dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": _("Alteração de Senha Obrigatória"),
                "subtitle": _("Por segurança, você deve escolher uma nova senha"),
                "is_required_change": True,
            }
        )
        return context

    def form_valid(self, form):
        """Clear the password change flag and log the security event."""
        response = super().form_valid(form)

        # Clear the flag with history tracking
        self.request.user.password_change_required = False
        self.request.user._change_reason = "Mandatory password change completed"
        self.request.user.save(update_fields=["password_change_required"])

        # Security logging
        from .history import get_client_ip

        logger.info(
            f"Mandatory password change completed for user {self.request.user.username} "
            f"from IP {get_client_ip(self.request)}"
        )

        # Success message
        messages.success(
            self.request, _("Senha alterada com sucesso! Bem-vindo ao sistema.")
        )

        return response

    def get_form_kwargs(self):
        """Add any additional form configuration."""
        kwargs = super().get_form_kwargs()
        return kwargs
