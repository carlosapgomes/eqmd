import re
from typing import Set, List, Dict


PLACEHOLDER_PATTERN = re.compile(r"{{(\w+)}}")
ALLOWED_PLACEHOLDERS = {
    "patient_name",
    "patient_record_number",
    "patient_birth_date",
    "patient_age",
    "patient_gender",
    "patient_fiscal_number",
    "patient_healthcard_number",
    "patient_ward",
    "patient_bed",
    "patient_status",
    "doctor_name",
    "doctor_profession",
    "doctor_registration_number",
    "doctor_specialty",
    "document_date",
    "document_datetime",
    "hospital_name",
    "hospital_city",
    "hospital_state",
    "hospital_address",
    "page_break",
}
REQUIRED_PLACEHOLDERS = {"patient_name"}
PAGE_BREAK_TOKEN = "<div style='page-break-after: always'></div>"


def extract_placeholders(template: str) -> Set[str]:
    """
    Extract all unique placeholders from a template string.

    Args:
        template: The template string containing placeholders in {{placeholder}} format

    Returns:
        Set of unique placeholder names
    """
    if not template:
        return set()

    matches = PLACEHOLDER_PATTERN.findall(template)
    return set(matches)


def _format_placeholder_list(placeholders: Set[str]) -> str:
    """
    Format a set of placeholders as a sorted, comma-separated string.

    Args:
        placeholders: Set of placeholder names

    Returns:
        Formatted string with sorted placeholders
    """
    return ', '.join(sorted(placeholders))


def _check_unknown_placeholders(placeholders: Set[str]) -> List[str]:
    """
    Check for placeholders that are not in the allowed list.

    Args:
        placeholders: Set of placeholder names to check

    Returns:
        List of error messages for unknown placeholders
    """
    unknown_placeholders = placeholders - ALLOWED_PLACEHOLDERS
    if unknown_placeholders:
        return [f"Unknown placeholders: {_format_placeholder_list(unknown_placeholders)}"]
    return []


def _check_missing_placeholders(placeholders: Set[str]) -> List[str]:
    """
    Check for missing required placeholders.

    Args:
        placeholders: Set of placeholder names to check

    Returns:
        List of error messages for missing placeholders
    """
    missing_placeholders = REQUIRED_PLACEHOLDERS - placeholders
    if missing_placeholders:
        return [f"Missing required placeholders: {_format_placeholder_list(missing_placeholders)}"]
    return []


def validate_template_placeholders(
    template: str,
    require_required: bool = True,
) -> List[str]:
    """
    Validate that a template only contains allowed placeholders and, optionally,
    includes required ones.

    Args:
        template: The template string to validate
        require_required: When True, enforce required placeholders.

    Returns:
        List of error messages (empty if validation passes)
    """
    placeholders = extract_placeholders(template)
    errors = []

    errors.extend(_check_unknown_placeholders(placeholders))
    if errors:
        return errors

    if require_required:
        errors.extend(_check_missing_placeholders(placeholders))

    return errors


def _check_missing_context_values(placeholders: Set[str], context: Dict[str, str]) -> None:
    """
    Check if all placeholders (except page_break) have values in context.

    Args:
        placeholders: Set of placeholder names to check
        context: Dictionary with placeholder values

    Raises:
        ValueError: If required placeholders are missing from context
    """
    missing_context_values = placeholders - context.keys() - {"page_break"}
    if missing_context_values:
        raise ValueError(f"Missing context values for placeholders: {_format_placeholder_list(missing_context_values)}")


def render_template(template: str, context: Dict[str, str]) -> str:
    """
    Render a template by substituting placeholders with values from context.

    Args:
        template: The template string with {{placeholder}} entries
        context: Dictionary mapping placeholder names to values

    Returns:
        Rendered string with placeholders substituted

    Raises:
        ValueError: If a placeholder in the template is missing from context
    """
    if not template:
        return ""

    placeholders = extract_placeholders(template)
    _check_missing_context_values(placeholders, context)

    result = template

    # Substitute each placeholder
    for placeholder in placeholders:
        placeholder_tag = f"{{{{{placeholder}}}}}"

        if placeholder == "page_break":
            result = result.replace(placeholder_tag, PAGE_BREAK_TOKEN)
        elif placeholder in context:
            result = result.replace(placeholder_tag, context[placeholder])

    return result
