from django.test import TestCase
from apps.reports.services.renderer import (
    extract_placeholders,
    validate_template_placeholders,
    render_template,
    PAGE_BREAK_TOKEN,
    ALLOWED_PLACEHOLDERS,
)


class TestPlaceholderExtraction(TestCase):
    def test_extract_single_placeholder(self):
        template = "Hello {{patient_name}}"
        placeholders = extract_placeholders(template)
        assert placeholders == {"patient_name"}

    def test_extract_multiple_placeholders(self):
        template = "{{patient_name}} - {{patient_record_number}}"
        placeholders = extract_placeholders(template)
        assert placeholders == {"patient_name", "patient_record_number"}

    def test_extract_duplicate_placeholders(self):
        template = "{{patient_name}} and {{patient_name}}"
        placeholders = extract_placeholders(template)
        assert placeholders == {"patient_name"}

    def test_extract_no_placeholders(self):
        template = "No placeholders here"
        placeholders = extract_placeholders(template)
        assert placeholders == set()

    def test_extract_placeholders_with_text(self):
        template = "Patient: {{patient_name}} has record {{patient_record_number}}"
        placeholders = extract_placeholders(template)
        assert placeholders == {"patient_name", "patient_record_number"}


class TestTemplateValidation(TestCase):
    def test_validate_rejects_unknown_placeholder(self):
        template = "Hello {{unknown_placeholder}}"
        errors = validate_template_placeholders(template)
        assert len(errors) > 0
        assert any("unknown_placeholder" in str(error) for error in errors)

    def test_validate_requires_patient_name(self):
        template = "Some text without required placeholders"
        errors = validate_template_placeholders(template)
        assert len(errors) > 0
        assert any("patient_name" in str(error) for error in errors)

    def test_validate_accepts_valid_template(self):
        template = "Patient: {{patient_name}}, Record: {{patient_record_number}}"
        errors = validate_template_placeholders(template)
        assert len(errors) == 0

    def test_validate_accepts_template_with_page_break(self):
        template = "Patient: {{patient_name}}, Record: {{patient_record_number}} {{page_break}} More text"
        errors = validate_template_placeholders(template)
        assert len(errors) == 0

    def test_validate_accepts_all_known_placeholders(self):
        template = " ".join(f"{{{{{name}}}}}" for name in sorted(ALLOWED_PLACEHOLDERS))
        errors = validate_template_placeholders(template)
        assert len(errors) == 0


class TestTemplateRendering(TestCase):
    def test_render_substitutes_values(self):
        template = "Patient: {{patient_name}}, Record: {{patient_record_number}}"
        context = {
            "patient_name": "John Doe",
            "patient_record_number": "12345"
        }
        result = render_template(template, context)
        assert result == "Patient: John Doe, Record: 12345"

    def test_render_page_break_token(self):
        template = "First page {{page_break}} Second page"
        context = {}
        result = render_template(template, context)
        assert PAGE_BREAK_TOKEN in result
        assert result == "First page <div style='page-break-after: always'></div> Second page"

    def test_render_missing_context_value_raises(self):
        template = "Patient: {{patient_name}}"
        context = {}  # Missing patient_name
        with self.assertRaises(ValueError) as context_manager:
            render_template(template, context)
        self.assertIn("patient_name", str(context_manager.exception))

    def test_render_preserves_text_outside_placeholders(self):
        template = "Start {{patient_name}} middle {{patient_record_number}} end"
        context = {
            "patient_name": "Jane Doe",
            "patient_record_number": "67890"
        }
        result = render_template(template, context)
        assert result == "Start Jane Doe middle 67890 end"

    def test_render_empty_template(self):
        template = ""
        context = {}
        result = render_template(template, context)
        assert result == ""
