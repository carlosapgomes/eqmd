# Phase 02 – OIDC Provider Setup Prompt ✅ COMPLETED (2025-01-12)

You are implementing Phase 02: OIDC Provider Setup.

## Instructions
Follow docs/02-oidc-provider-setup.md exactly.

## Goal
Install django-oidc-provider and configure with ZERO behavior change.

## Tasks
1. Install django-oidc-provider and pyjwt
2. Add to INSTALLED_APPS
3. Run migrations
4. Generate RSA key
5. Configure OIDC settings
6. Create botauth app structure
7. Verify no regression

## Critical Constraints
- Existing allauth login MUST still work
- No API behavior changes
- No new public endpoints exposed

## Verification
```bash
uv run python -c "import oidc_provider; print('OK')"
uv run python manage.py showmigrations oidc_provider
uv run pytest apps/accounts/tests/ -v  # Must pass
```
