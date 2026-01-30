import re
from django.core.exceptions import ValidationError


PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

ALLOWED_PLACEHOLDERS = {
    "patient_name",
    "patient_record_number",
    "document_date",
    "procedure_description",
}

REQUIRED_PLACEHOLDERS = {
    "patient_name",
    "patient_record_number",
    "document_date",
}


def extract_placeholders(markdown_text):
    if not markdown_text:
        return set()
    return set(PLACEHOLDER_PATTERN.findall(markdown_text))


def validate_template_placeholders(markdown_text):
    placeholders = extract_placeholders(markdown_text)

    unknown = placeholders - ALLOWED_PLACEHOLDERS
    if unknown:
        raise ValidationError(
            f"Unknown placeholders: {', '.join(sorted(unknown))}"
        )

    missing = REQUIRED_PLACEHOLDERS - placeholders
    if missing:
        raise ValidationError(
            f"Missing required placeholders: {', '.join(sorted(missing))}"
        )

    return placeholders


def render_template(markdown_text, context):
    placeholders = extract_placeholders(markdown_text)

    unknown = placeholders - ALLOWED_PLACEHOLDERS
    if unknown:
        raise ValidationError(
            f"Unknown placeholders: {', '.join(sorted(unknown))}"
        )

    missing_required = REQUIRED_PLACEHOLDERS - placeholders
    if missing_required:
        raise ValidationError(
            f"Missing required placeholders: {', '.join(sorted(missing_required))}"
        )

    missing_values = [
        key for key in placeholders
        if key not in context or context.get(key) in (None, "")
    ]
    if missing_values:
        raise ValidationError(
            f"Missing values for placeholders: {', '.join(sorted(missing_values))}"
        )

    def replace(match):
        key = match.group(1)
        value = context.get(key)
        if value in (None, ""):
            raise ValidationError(f"Missing value for placeholder: {key}")
        return str(value)

    return PLACEHOLDER_PATTERN.sub(replace, markdown_text)
