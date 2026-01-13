"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from allauth.account.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordResetView, 
    PasswordResetDoneView, PasswordResetFromKeyView, PasswordResetFromKeyDoneView,
    EmailView, ConfirmEmailView
)
from apps.core.views import SignupBlockedView

urlpatterns = [
    path(
        "favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=True)
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("", include("apps.core.urls", namespace="core")),
    path("admin/", admin.site.urls),
    # Explicit allauth URLs without signup
    path("accounts/login/", LoginView.as_view(), name="account_login"),
    path("accounts/logout/", LogoutView.as_view(), name="account_logout"),
    path("accounts/password/change/", PasswordChangeView.as_view(), name="account_change_password"),
    path("accounts/password/reset/", PasswordResetView.as_view(), name="account_reset_password"),
    path("accounts/password/reset/done/", PasswordResetDoneView.as_view(), name="account_reset_password_done"),
    re_path(r"^accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$", PasswordResetFromKeyView.as_view(), name="account_reset_password_from_key"),
    path("accounts/password/reset/key/done/", PasswordResetFromKeyDoneView.as_view(), name="account_reset_password_from_key_done"),
    path("accounts/email/", EmailView.as_view(), name="account_email"),
    path("accounts/confirm-email/", TemplateView.as_view(template_name="account/verification_sent.html"), name="account_email_verification_sent"),
    path("accounts/confirm-email/<key>/", ConfirmEmailView.as_view(), name="account_confirm_email"),
    # Block signup attempts with custom view
    path("accounts/signup/", SignupBlockedView.as_view(), name="account_signup"),
    path("profiles/", include("apps.accounts.urls", namespace="apps.accounts")),
    path("patients/", include("apps.patients.urls", namespace="patients")),
    path("events/", include("apps.events.urls", namespace="events")),
    path("dailynotes/", include("apps.dailynotes.urls", namespace="dailynotes")),
    path("simplenotes/", include("apps.simplenotes.urls", namespace="simplenotes")),
    path("mediafiles/", include("apps.mediafiles.urls", namespace="mediafiles")),
    path(
        "historyandphysicals/",
        include("apps.historyandphysicals.urls", namespace="historyandphysicals"),
    ),
    path(
        "sample-content/",
        include("apps.sample_content.urls", namespace="sample_content"),
    ),
    path(
        "drugtemplates/",
        include("apps.drugtemplates.urls", namespace="drugtemplates"),
    ),
    path(
        "prescriptions/",
        include("apps.outpatientprescriptions.urls", namespace="outpatientprescriptions"),
    ),
    path("pdf/", include("apps.pdfgenerator.urls", namespace="pdfgenerator")),
    path("pdf-forms/", include("apps.pdf_forms.urls", namespace="pdf_forms")),
    path("dischargereports/", include("apps.dischargereports.urls")),
    path("research/", include("apps.research.urls", namespace="apps.research")),
    path("auth/", include("apps.botauth.urls", namespace="botauth")),
    # OIDC Provider endpoints (minimal exposure)
    # We only need the token endpoint for client_credentials
    path("o/", include("oidc_provider.urls", namespace="oidc_provider")),
]

# Custom error handlers
handler403 = 'apps.core.views.custom_permission_denied_view'
handler404 = 'apps.core.views.custom_page_not_found_view'
handler500 = 'apps.core.views.custom_server_error_view'

# Serve media and static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]
    )
