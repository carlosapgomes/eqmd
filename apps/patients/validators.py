import re
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

CPF_LENGTH = 11
CNS_LENGTH = 15
_CPF_FIRST_WEIGHTS = (10, 9, 8, 7, 6, 5, 4, 3, 2)
_CPF_SECOND_WEIGHTS = (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)
_CNS_PIS_WEIGHTS = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNS_PROVISORY_WEIGHTS = (4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
_CNS_DEFINITIVE_SUFFIX = "0001"
_NON_DIGIT = re.compile(r"\D")

# Reserved prefix for server-generated temporary record numbers. Defined in
# this import-free base module so services, forms and models share one
# constant without import cycles.
TEMPORARY_RECORD_PREFIX = "TMP-"


def validate_record_number_format(record_number):
    """Validate record number format (customize based on hospital requirements)"""
    if not record_number or not record_number.strip():
        raise ValidationError("Número do prontuário não pode estar vazio")

    # Example validation - customize based on hospital requirements
    if len(record_number.strip()) < 3:
        raise ValidationError("Número do prontuário deve ter pelo menos 3 caracteres")

    # Placeholder-only values (e.g. "---") carry no identity and must never
    # become a record number on any write path.
    if not any(character.isalnum() for character in record_number.strip()):
        raise ValidationError(
            "Número do prontuário deve conter ao menos uma letra ou número"
        )

    # Add more specific validation rules as needed
    # e.g., regex patterns, check digits, etc.


TEMPORARY_RECORD_NUMBER_MESSAGE = (
    "Números iniciados em TMP- são reservados para registros temporários "
    "gerados pelo sistema."
)


def validate_permanent_record_number(record_number):
    """Reject manually typed numbers that use the reserved TMP- prefix.

    Pure prefix gate, separate from ``validate_record_number_format``:
    generated temporaries satisfy the base format, so only the manual
    write doors call this validation.
    """
    if record_number.strip().upper().startswith(TEMPORARY_RECORD_PREFIX):
        raise ValidationError(TEMPORARY_RECORD_NUMBER_MESSAGE)


def validate_admission_datetime(admission_datetime):
    """Validate admission datetime"""
    if not admission_datetime:
        raise ValidationError("Data/hora de admissão é obrigatória")

    # Can't be in the future (allow some buffer for clock differences)
    if admission_datetime > timezone.now() + timedelta(minutes=5):
        raise ValidationError("Data de admissão não pode ser no futuro")

    # Can't be too far in the past (customize based on requirements)
    if admission_datetime < timezone.now() - timedelta(days=365):
        raise ValidationError("Data de admissão não pode ser superior a 1 ano atrás")


def validate_discharge_datetime(discharge_datetime, admission_datetime):
    """Validate discharge datetime against admission"""
    if not discharge_datetime:
        return  # Discharge is optional

    if not admission_datetime:
        raise ValidationError(
            "Data de admissão deve estar definida para registrar alta"
        )

    if discharge_datetime <= admission_datetime:
        raise ValidationError("Data de alta deve ser posterior à data de admissão")

    # Can't be in the future
    if discharge_datetime > timezone.now() + timedelta(minutes=5):
        raise ValidationError("Data de alta não pode ser no futuro")

    # Check for reasonable stay duration (customize based on requirements)
    stay_duration = discharge_datetime - admission_datetime
    if stay_duration.days > 365:
        raise ValidationError("Duração da internação parece muito longa (>365 dias)")


def normalize_cpf(value: str) -> str:
    """Return CPF digits only."""
    return _digits_only(value)


def normalize_cns(value: str) -> str:
    """Return CNS digits only."""
    return _digits_only(value)


def _digits_only(value: str) -> str:
    """Strip every non-digit character from a value."""
    return _NON_DIGIT.sub("", value or "")


def is_valid_cpf(value: str) -> bool:
    """True for an 11-digit canonical CPF with two valid check digits."""
    if len(value) != CPF_LENGTH or value == value[0] * CPF_LENGTH:
        return False
    digits = [int(char) for char in value]
    first_check = _cpf_check_digit(digits[:9], _CPF_FIRST_WEIGHTS)
    second_check = _cpf_check_digit(digits[:10], _CPF_SECOND_WEIGHTS)
    return digits[9] == first_check and digits[10] == second_check


def _cpf_check_digit(digits: list[int], weights: tuple[int, ...]) -> int:
    """Compute one CPF check digit using the official weighted rule."""
    remainder = sum(digit * weight for digit, weight in zip(digits, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder


def is_valid_cns(value: str) -> bool:
    """True for a 15-digit canonical CNS valid under the official rule.

    Definitive CNS (first digit 1 or 2) use the PIS-style check digit on
    digits 1-10 and must end with the "0001" suffix; provisory CNS (first
    digit 7, 8, or 9) use the official 15-digit weighted sum; any other
    prefix is invalid (Portaria SAS/MS 174/2000).
    """
    if len(value) != CNS_LENGTH:
        return False
    first = value[0]
    if first in "12":
        remainder = (
            sum(int(char) * weight for char, weight in zip(value, _CNS_PIS_WEIGHTS))
            % 11
        )
        dv = 11 - remainder
        if dv == 10:
            dv = 0
        return value[10] == str(dv) and value[11:] == _CNS_DEFINITIVE_SUFFIX
    if first in "789":
        total = sum(
            int(char) * weight for char, weight in zip(value, _CNS_PROVISORY_WEIGHTS)
        )
        return total % 11 == 0
    return False


def validate_cpf(value: str) -> None:
    """Raise ValidationError unless value is a valid canonical CPF."""
    if not is_valid_cpf(value):
        raise ValidationError("CPF inválido.")


def validate_cns(value: str) -> None:
    """Raise ValidationError unless value is a valid canonical CNS."""
    if not is_valid_cns(value):
        raise ValidationError("CNS inválido.")


def validate_patient_admission_state(patient):
    """Validate patient's overall admission state for consistency"""
    active_admissions = patient.admissions.filter(is_active=True)

    if active_admissions.count() > 1:
        raise ValidationError("Paciente não pode ter múltiplas internações ativas")

    if patient.status == patient.Status.INPATIENT and not active_admissions.exists():
        raise ValidationError(
            "Paciente marcado como internado mas sem internação ativa"
        )

    if patient.status != patient.Status.INPATIENT and active_admissions.exists():
        raise ValidationError(
            "Paciente tem internação ativa mas status indica que não está internado"
        )
