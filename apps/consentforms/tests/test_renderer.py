from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.consentforms.services.renderer import render_template, validate_template_placeholders


class ConsentTemplateRendererTests(TestCase):
    def test_validate_template_success(self):
        template = (
            "Consentimento para {{ patient_name }} ({{ patient_record_number }}) "
            "em {{ document_date }}. Procedimento: {{ procedure_description }}."
        )
        placeholders = validate_template_placeholders(template)
        self.assertIn("patient_name", placeholders)

    def test_validate_template_unknown_placeholder(self):
        template = "Teste {{ patient_name }} {{ unknown_field }}"
        with self.assertRaises(ValidationError):
            validate_template_placeholders(template)

    def test_validate_template_missing_required(self):
        template = "Consentimento {{ patient_name }} {{ document_date }}"
        with self.assertRaises(ValidationError):
            validate_template_placeholders(template)

    def test_render_template_replaces_placeholders(self):
        template = "{{ patient_name }} - {{ patient_record_number }} - {{ document_date }}"
        rendered = render_template(
            template,
            {
                "patient_name": "Ana Silva",
                "patient_record_number": "12345",
                "document_date": "01/01/2026",
            },
        )
        self.assertEqual(rendered, "Ana Silva - 12345 - 01/01/2026")

    def test_render_template_missing_value(self):
        template = "{{ patient_name }} {{ document_date }} {{ patient_record_number }}"
        with self.assertRaises(ValidationError):
            render_template(template, {"patient_name": "Ana"})

    def test_page_break_placeholder(self):
        template = "{{ patient_name }}{{ page_break }}{{ patient_record_number }}"
        rendered = render_template(
            template,
            {"patient_name": "Ana", "patient_record_number": "123"},
        )
        self.assertIn("<<PAGE_BREAK>>", rendered)
