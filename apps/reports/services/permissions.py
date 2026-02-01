"""
Permission service for reports app.
"""

from apps.core.permissions.utils import is_doctor_or_resident


def can_manage_report_templates(user) -> bool:
    """
    Check if a user can manage report templates.

    Users who can manage templates:
    - Admin/staff users (is_staff or is_superuser)
    - Doctors (profession_type = MEDICAL_DOCTOR)
    - Residents (profession_type = RESIDENT)

    Args:
        user: The user to check

    Returns:
        bool: True if user can manage templates, False otherwise
    """
    if user is None:
        return False

    if not getattr(user, 'is_authenticated', False):
        return False

    # Staff and superuser can manage templates
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True

    # Doctors and residents can manage templates
    return is_doctor_or_resident(user)
