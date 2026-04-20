"""
Shared test helpers for the accounts app.

These helpers are intentionally kept independent of factory_boy
so they can be imported in any test environment without extra deps.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


def create_navigation_user(**kwargs):
    """Create a User via ORM with lifecycle gates cleared.

    Thin wrapper around User.objects.create_user() that forces sensible
    defaults for view/API tests that are NOT testing lifecycle middleware:

        password_change_required=False  (skip PasswordChangeRequiredMiddleware)
        terms_accepted=True             (skip TermsAcceptanceRequiredMiddleware)

    Any of these defaults can be overridden by passing explicit keyword
    arguments (e.g. for a test that *does* want to verify a specific gate).

    Returns the saved user instance.
    """
    kwargs.setdefault('password_change_required', False)
    kwargs.setdefault('terms_accepted', True)
    return User.objects.create_user(**kwargs)
