# apps/pdf_forms/permissions.py
from django.core.exceptions import PermissionDenied

from apps.core.permissions.utils import can_access_patient


def check_pdf_form_access(user, patient):
    """Check if user can access PDF forms for patient."""
    if not can_access_patient(user, patient):
        raise PermissionDenied(
            "You don't have permission to access this patient's PDF forms"
        )

    return True


def check_pdf_form_creation(user, patient):
    """Check if user can create PDF forms for patient."""
    # Add any additional checks for PDF form creation
    return check_pdf_form_access(user, patient)


def check_pdf_form_template_access(user):
    """Check if user can access PDF form templates."""
    # All authenticated users can view available templates
    return user.is_authenticated


def check_pdf_form_template_management(user):
    """Check if user can manage PDF form templates."""
    # Only superusers can create/edit/delete templates; a missing user is denied.
    if user is None or not user.is_superuser:
        raise PermissionDenied("Only administrators can manage PDF form templates")

    return True


def check_pdf_download_access(user, submission):
    """Check if user can download a PDF form submission."""
    # Missing submission is denied rather than crashing on attribute access.
    if submission is None:
        raise PermissionDenied("Cannot generate PDF: form data is missing")

    # User must have access to the patient
    if not check_pdf_form_access(user, submission.patient):
        return False

    # Validate that form_data exists and is valid for PDF generation
    if not submission.form_data:
        raise PermissionDenied("Cannot generate PDF: form data is missing")

    # Ensure form data is properly structured
    if not isinstance(submission.form_data, dict):
        raise PermissionDenied("Cannot generate PDF: invalid form data structure")

    return True


