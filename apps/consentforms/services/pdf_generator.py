from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, Spacer

from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator
from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser
from .renderer import PAGE_BREAK_TOKEN


class ConsentFormPDFGenerator(HospitalLetterheadGenerator):
    """PDF generator for consent forms with a dedicated layout entry point."""

    def __init__(self):
        super().__init__()
        self.markdown_parser = MarkdownToPDFParser(self.styles)
        self._document_date = None

    def _format_document_date(self, document_date):
        month_names = [
            "janeiro",
            "fevereiro",
            "março",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ]
        month_name = month_names[document_date.month - 1]
        return f"{document_date.day} de {month_name} de {document_date.year}"

    def _build_location_line(self, document_date):
        city = (self.hospital_config.get("city") or "").strip()
        state = (self.hospital_config.get("state_full") or "").strip()
        date_text = self._format_document_date(document_date)

        if city and state:
            return f"{city} - {state}, {date_text}"
        if city:
            return f"{city}, {date_text}"
        return date_text

    def _create_signature_section(self, doctor_info):
        document_date = self._document_date
        if document_date is None:
            from django.utils import timezone
            document_date = timezone.localdate()
        # content = [Spacer(1, 24)]
        content = [Spacer(1, 12)]
        location_line = self._build_location_line(document_date)

        date_style = ParagraphStyle(
            name="ConsentDate",
            parent=self.styles["PatientInfo"],
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=12,
        )
        content.append(Paragraph(location_line, date_style))
        content.append(Spacer(1, 12))
        # content.append(Spacer(1, 24))
        content.append(Paragraph("_" * 60, self.styles["Signature"]))

        doctor_name = (
            doctor_info.get("name", "Médico Responsável")
            if doctor_info
            else "Médico Responsável"
        )
        profession = (
            doctor_info.get("profession", "Médico") if doctor_info else "Médico"
        )
        registration_number = (
            doctor_info.get("registration_number", "") if doctor_info else ""
        )
        crm_field = registration_number if registration_number else "_______________"

        content.append(
            Paragraph(
                f"<b>{doctor_name}</b><br/>{profession} - CRM: {crm_field}<br/><b>Assinatura e Carimbo</b>",
                self.styles["Signature"],
            )
        )

        return content

    def generate_from_consent(self, consent_form):
        content_elements = []
        parts = consent_form.rendered_markdown.split(PAGE_BREAK_TOKEN)
        for index, part in enumerate(parts):
            part = part.strip()
            if part:
                content_elements.extend(self.markdown_parser.parse(part))
            if index < len(parts) - 1:
                content_elements.append(PageBreak())

        patient_data = {}

        doctor = consent_form.created_by
        doctor_info = {
            "name": doctor.get_full_name() or doctor.username,
            "profession": getattr(doctor, "profession", "Médico"),
            "registration_number": getattr(doctor, "professional_registration_number", ""),
        }

        self._document_date = consent_form.document_date
        return self.generate_pdf(
            content_elements=content_elements,
            document_title="",
            patient_data=patient_data,
            doctor_info=doctor_info,
        )
