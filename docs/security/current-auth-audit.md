# Current Authentication Audit

## Date: 2025-01-12

## Auditor: Claude Code (Phase 01 Baseline Assessment)

### Authentication Backends (settings.py)

- [x] django.contrib.auth.backends.ModelBackend
- [x] allauth.account.auth_backends.AuthenticationBackend  
- [x] apps.core.backends.EquipeMedPermissionBackend

### DRF Authentication Classes

- [x] rest_framework.authentication.SessionAuthentication

### Middleware Stack

(Listed in order of execution)
1. django.middleware.security.SecurityMiddleware
2. django.contrib.sessions.middleware.SessionMiddleware
3. django.middleware.common.CommonMiddleware
4. django.middleware.csrf.CsrfViewMiddleware
5. django.contrib.auth.middleware.AuthenticationMiddleware
6. allauth.account.middleware.AccountMiddleware
7. simple_history.middleware.HistoryRequestMiddleware
8. apps.core.middleware.EnhancedHistoryMiddleware
9. apps.core.middleware.PasswordChangeRequiredMiddleware
10. apps.core.middleware.TermsAcceptanceRequiredMiddleware
11. apps.core.middleware.UserLifecycleMiddleware
12. django.contrib.messages.middleware.MessageMiddleware
13. django.middleware.clickjacking.XFrameOptionsMiddleware

### Session Configuration

- ENGINE: django.contrib.sessions.backends.cached_db
- SESSION_CACHE_ALIAS: default
- SESSION_COOKIE_SECURE: Environment-controlled (False in dev, True in prod)
- CSRF_COOKIE_SECURE: Environment-controlled (False in dev, True in prod)

### allauth Configuration

- ACCOUNT_LOGIN_METHODS: {"email"} (email-only login)
- ACCOUNT_EMAIL_VERIFICATION: mandatory (environment-controlled)
- ACCOUNT_ALLOW_REGISTRATION: False (signup disabled)
- ACCOUNT_OPEN_SIGNUP: False
- ACCOUNT_REGISTRATION_CLOSED: True
- ACCOUNT_SIGNUP_ENABLED: False
- ACCOUNT_PREVENT_ENUMERATION: True
- ACCOUNT_RATE_LIMITS: login_failed: '5/m', signup: '0/m'

### Custom User Model

- AUTH_USER_MODEL: "accounts.EqmdCustomUser"

### Security Settings

- CSRF_TRUSTED_ORIGINS: Environment-controlled
- SECURE_PROXY_SSL_HEADER: ("HTTP_X_FORWARDED_PROTO", "https")
- USE_X_FORWARDED_HOST: True

### Rate Limiting

- Login failed attempts: 5 per minute
- Signup attempts: 0 (blocked completely)

### Password Management

- Password reset timeout: 86400 seconds (24 hours)
- Password validation: Django default validators enabled

### Audit Trail Support

- simple_history: Enabled with UUID history IDs
- EnhancedHistoryMiddleware: IP tracking and user agent logging
- HistoryRequestMiddleware: Request tracking for history

### User Lifecycle Management

- Activity tracking: Enabled
- Auto status updates: Enabled
- Inactivity threshold: 90 days
- Expiration warnings: [30, 14, 7, 3, 1] days before expiration