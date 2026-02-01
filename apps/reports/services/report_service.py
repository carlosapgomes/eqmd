"""
Report service for creating reports from templates.

Provides functions to render templates and create Report instances.
"""
from datetime import date
from typing import Optional

from django.utils import timezone

from apps.reports.models import ReportTemplate, Report
from apps.reports.services.renderer import render_template
from apps.reports.services.context_builder import build_report_context


class ReportServiceError(Exception):
    """Exception raised for errors in the report service."""
    pass


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
    # Build context for rendering
    context = build_report_context(
        patient=patient,
        doctor=doctor,
        document_date=document_date,
    )

    # Render template content
    try:
        rendered_content = render_template(template.markdown_body, context)
    except ValueError as e:
        raise ReportServiceError(f"Template rendering failed: {e}")

    # Use template name as default title if not provided
    report_title = title if title is not None else template.name

    # Create the report
    report = Report(
        patient=patient,
        created_by=created_by,
        updated_by=created_by,
        description=f"Relatório - {template.name}",
        event_datetime=timezone.now(),
        content=rendered_content,
        document_date=document_date,
        title=report_title,
        template=template,
    )
    report.save()

    return report
