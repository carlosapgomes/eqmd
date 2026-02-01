"""
Context builder service for report rendering.

Provides deterministic placeholder context building for patient, doctor,
document, and hospital fields.
"""
from datetime import date
from typing import Dict

from apps.reports.services.renderer import PAGE_BREAK_TOKEN


def _build_patient_context(patient) -> Dict[str, str]:
    """
    Build context dictionary for patient-related placeholders.

    Args:
        patient: The patient model instance

    Returns:
        Dictionary with patient_name and patient_record_number
    """
    record_number = ""
    if hasattr(patient, 'current_record_number'):
        record_number = patient.current_record_number or ""
    if not record_number and hasattr(patient, 'get_current_record_number'):
        record_number = patient.get_current_record_number() or ""

    return {
        "patient_name": patient.name,
        "patient_record_number": record_number,
    }


def _build_doctor_context(doctor) -> Dict[str, str]:
    """
    Build context dictionary for doctor-related placeholders.

    Args:
        doctor: The user model instance representing the doctor

    Returns:
        Dictionary with doctor_name
    """
    doctor_name = ""
    if doctor:
        # Try profile display_name first
        if hasattr(doctor, 'profile') and doctor.profile:
            doctor_name = doctor.profile.display_name or ""
        # Fall back to get_full_name()
        if not doctor_name and hasattr(doctor, 'get_full_name'):
            doctor_name = doctor.get_full_name() or ""
        # Last resort: first_name + last_name
        if not doctor_name:
            doctor_name = f"{doctor.first_name} {doctor.last_name}".strip()
        # Ultimate fallback: username
        if not doctor_name:
            doctor_name = doctor.username

    return {
        "doctor_name": doctor_name,
    }


def _build_document_context(document_date: date) -> Dict[str, str]:
    """
    Build context dictionary for document-related placeholders.

    Args:
        document_date: The date of the document

    Returns:
        Dictionary with document_date formatted as DD/MM/YYYY
    """
    return {
        "document_date": document_date.strftime("%d/%m/%Y"),
    }


def build_report_context(
    patient,
    doctor,
    document_date: date,
) -> Dict[str, str]:
    """
    Build complete context dictionary for report template rendering.

    Combines patient, doctor, and document contexts into a single dictionary
    suitable for use with render_template().

    Args:
        patient: The patient model instance
        doctor: The user model instance representing the doctor
        document_date: The date of the document

    Returns:
        Dictionary with all placeholder values:
        - patient_name: Patient's full name
        - patient_record_number: Patient's current record number
        - doctor_name: Doctor's full name
        - document_date: Formatted document date (DD/MM/YYYY)
        - page_break: Page break token for PDF generation
    """
    context = {}

    # Add patient fields
    context.update(_build_patient_context(patient))

    # Add doctor fields
    context.update(_build_doctor_context(doctor))

    # Add document fields
    context.update(_build_document_context(document_date))

    # Add page_break token
    context["page_break"] = PAGE_BREAK_TOKEN

    return context
