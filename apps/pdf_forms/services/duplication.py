"""
Duplication eligibility service for PDF form templates and submissions.

Business rules are centralized here to keep views and templates clean.
"""
from typing import Any

from django import forms

from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.core.permissions.utils import can_access_patient


def is_template_duplication_supported(template: PDFFormTemplate) -> bool:
    """
    Check whether a PDFFormTemplate supports duplication.

    A template supports duplication only when ALL conditions are met:
    - Template is active.
    - Template form_type is ``HOSPITAL``.
    - Template opt-in flag ``allow_duplication`` is enabled.

    APAC and AIH templates are **never** supported even if the flag is on.
    """
    if not template.is_active:
        return False
    if template.form_type != "HOSPITAL":
        return False
    if not template.allow_duplication:
        return False
    return True


def can_duplicate_pdf_submission(
    user: Any,
    submission: PDFFormSubmission,
) -> bool:
    """
    Check whether a user can duplicate a specific PDF form submission.

    Returns ``True`` only when ALL conditions are met:
    - The submission's template supports duplication.
    - The user can access the patient.
    - The user has the ``events.add_event`` permission.
    """
    if not is_template_duplication_supported(submission.form_template):
        return False
    if not can_access_patient(user, submission.patient):
        return False
    if not user.has_perm("events.add_event"):
        return False
    return True


def build_duplicate_initial_data(
    form_class: type[forms.Form],
    source_form_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Build initial data for a duplicate form from source submission data.

    Starts with the normal auto-fill initial values from the form class,
    then overlays compatible keys from the source ``form_data``.

    If the form has a ``_procedure_search_config`` and the source contains
    ``procedure_code`` and ``procedure_description``, the synthetic
    ``procedure_display`` field is initialized as
    ``"<code> - <description>"``.

    Unknown source keys are tolerated and silently ignored.
    """
    initial = {}

    # Start with normal auto-fill initial values
    if hasattr(form_class, '_patient_initial_values'):
        initial.update(form_class._patient_initial_values)

    # Overlay matching source form_data values
    for key, value in source_form_data.items():
        if key in form_class.base_fields:
            initial[key] = value

    # Initialize procedure display field if applicable
    proc_config = getattr(form_class, '_procedure_search_config', None)
    if proc_config:
        code = source_form_data.get(proc_config['code_field'])
        description = source_form_data.get(proc_config['description_field'])
        if code and description:
            display_field = proc_config['display_field']
            initial[display_field] = f"{code} - {description}"
            # Also ensure hidden fields are preserved
            initial[proc_config['code_field']] = code
            initial[proc_config['description_field']] = description

    return initial
