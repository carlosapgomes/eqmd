"""
Report service for creating reports from templates.

Provides functions to render templates and create Report instances.
"""
from datetime import date
from typing import Optional, Tuple

from django.utils import timezone

from apps.reports.models import ReportTemplate, Report
from apps.reports.services.renderer import render_template
from apps.reports.services.context_builder import build_report_context


class ReportServiceError(Exception):
    """Exception raised for errors in the report service."""
    pass


def _render_template_content(template: ReportTemplate, patient, doctor, document_date: date) -> str:
    """Render template markdown with context."""
    context = build_report_context(
        patient=patient,
        doctor=doctor,
        document_date=document_date,
    )
    return render_template(template.markdown_body, context)


def _create_report_instance(template: ReportTemplate, patient, created_by,
                            document_date: date, content: str, title: Optional[str]) -> Report:
    """Create and save a Report instance."""
    report_title = title if title is not None else template.name
    report = Report(
        patient=patient,
        created_by=created_by,
        updated_by=created_by,
        description=f"Relatório - {template.name}",
        event_datetime=timezone.now(),
        content=content,
        document_date=document_date,
        title=report_title,
        template=template,
    )
    report.save()
    return report


def create_report_from_template(
    template: ReportTemplate,
    patient,
    doctor,
    document_date: date,
    created_by,
    title: Optional[str] = None,
) -> Report:
    """
    Create a new report from a template with rendered placeholders.

    This function:
    1. Builds the context from patient, doctor, and document data
    2. Renders the template with the context
    3. Creates and saves a new Report instance

    Args:
        template: The ReportTemplate to use
        patient: The patient model instance
        doctor: The user model instance representing the doctor
        document_date: The date of the document
        created_by: The user creating the report
        title: Optional title (defaults to template name)

    Returns:
        The newly created Report instance

    Raises:
        ReportServiceError: If template rendering fails
    """
    try:
        rendered_content = _render_template_content(template, patient, doctor, document_date)
    except ValueError as e:
        raise ReportServiceError(f"Template rendering failed: {e}")

    return _create_report_instance(template, patient, created_by, document_date, rendered_content, title)


def can_user_use_template(user, template: ReportTemplate) -> bool:
    """Check if user can use a template (public or own)."""
    return template.is_public or template.created_by == user


def get_template_for_initial_content(template_id: str, user, patient, document_date: date
                                     ) -> Tuple[Optional[ReportTemplate], Optional[str]]:
    """
    Get template and render initial content for form.

    Returns:
        Tuple of (template, rendered_content) or (None, None) if template not accessible
    """
    try:
        template = ReportTemplate.objects.get(pk=template_id)
    except ReportTemplate.DoesNotExist:
        return None, None

    if not can_user_use_template(user, template):
        return None, None

    content = _render_template_content(template, patient, user, document_date)
    return template, content
