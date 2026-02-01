"""
Context builder service for report rendering.

Provides deterministic placeholder context building for patient, doctor,
document, and hospital fields.
"""
from datetime import date
from typing import Dict

from django.conf import settings
from django.utils import timezone

from apps.reports.services.renderer import PAGE_BREAK_TOKEN


def _format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _safe_string(value) -> str:
    return "" if value is None else str(value)


def _build_patient_context(patient) -> Dict[str, str]:
    """
    Build context dictionary for patient-related placeholders.

    Args:
        patient: The patient model instance

    Returns:
        Dictionary with patient fields for placeholders
    """
    record_number = ""
    if hasattr(patient, 'current_record_number'):
        record_number = patient.current_record_number or ""
    if not record_number and hasattr(patient, 'get_current_record_number'):
        record_number = patient.get_current_record_number() or ""

    birth_date = getattr(patient, "birthday", None)
    gender = ""
    if hasattr(patient, "get_gender_display"):
        gender = patient.get_gender_display() or ""
    elif hasattr(patient, "gender"):
        gender = patient.gender or ""

    ward_name = ""
    ward = getattr(patient, "ward", None)
    if ward:
        ward_name = ward.abbreviation or ward.name or ""

    status = ""
    if hasattr(patient, "get_status_display"):
        status = patient.get_status_display() or ""
    elif hasattr(patient, "status"):
        status = str(patient.status)

    age_value = ""
    if hasattr(patient, "age"):
        age_value = patient.age

    return {
        "patient_name": patient.name,
        "patient_record_number": record_number,
        "patient_birth_date": _format_date(birth_date),
        "patient_age": _safe_string(age_value),
        "patient_gender": gender,
        "patient_fiscal_number": getattr(patient, "fiscal_number", "") or "",
        "patient_healthcard_number": getattr(patient, "healthcard_number", "") or "",
        "patient_ward": ward_name,
        "patient_bed": getattr(patient, "bed", "") or "",
        "patient_status": status,
    }


def _build_doctor_context(doctor) -> Dict[str, str]:
    """
    Build context dictionary for doctor-related placeholders.

    Args:
        doctor: The user model instance representing the doctor

    Returns:
        Dictionary with doctor fields for placeholders
    """
    doctor_name = ""
    profession = ""
    registration_number = ""
    specialty = ""
    if doctor:
        # Try profile display_name first
        if hasattr(doctor, 'profile') and doctor.profile:
            doctor_name = doctor.profile.display_name or ""
            profession = doctor.profile.profession or ""
            specialty = doctor.profile.current_specialty_display or ""
        # Fall back to get_full_name()
        if not doctor_name and hasattr(doctor, 'get_full_name'):
            doctor_name = doctor.get_full_name() or ""
        # Last resort: first_name + last_name
        if not doctor_name:
            doctor_name = f"{doctor.first_name} {doctor.last_name}".strip()
        # Ultimate fallback: username
        if not doctor_name:
            doctor_name = doctor.username
        if not profession and hasattr(doctor, "get_profession_type_display"):
            profession = doctor.get_profession_type_display() or ""
        if not specialty:
            specialty = getattr(doctor, "specialty_display", "") or ""
        registration_number = getattr(doctor, "professional_registration_number", "") or ""

    return {
        "doctor_name": doctor_name,
        "doctor_profession": profession,
        "doctor_registration_number": registration_number,
        "doctor_specialty": specialty,
    }


def _build_document_context(document_date: date) -> Dict[str, str]:
    """
    Build context dictionary for document-related placeholders.

    Args:
        document_date: The date of the document

    Returns:
        Dictionary with document_date formatted as DD/MM/YYYY and document_datetime
    """
    date_text = _format_date(document_date)
    now = timezone.localtime()
    time_text = now.strftime("%H:%M")
    return {
        "document_date": date_text,
        "document_datetime": f"{date_text} {time_text}" if date_text else now.strftime("%d/%m/%Y %H:%M"),
    }


def _build_hospital_context() -> Dict[str, str]:
    """
    Build context dictionary for hospital-related placeholders.

    Returns:
        Dictionary with hospital name, city, state, and address
    """
    hospital_config = getattr(settings, "HOSPITAL_CONFIG", {})
    return {
        "hospital_name": hospital_config.get("name", "") or "",
        "hospital_city": hospital_config.get("city", "") or "",
        "hospital_state": hospital_config.get("state_full", "") or hospital_config.get("state", "") or "",
        "hospital_address": hospital_config.get("address", "") or "",
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
        - patient_*: Patient identifiers and demographics
        - doctor_*: Doctor identifiers and specialty
        - document_date/document_datetime: Formatted document date/time
        - hospital_*: Hospital configuration values
        - page_break: Page break token for PDF generation
    """
    context = {}

    # Add patient fields
    context.update(_build_patient_context(patient))

    # Add doctor fields
    context.update(_build_doctor_context(doctor))

    # Add document fields
    context.update(_build_document_context(document_date))

    # Add hospital fields
    context.update(_build_hospital_context())

    # Add page_break token
    context["page_break"] = PAGE_BREAK_TOKEN

    return context
