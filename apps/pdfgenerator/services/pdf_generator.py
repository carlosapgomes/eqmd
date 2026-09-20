"""
Base PDF generation service with hospital letterhead template.
"""

import io

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.colors import black, darkblue
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.flowables import Flowable

from apps.pdfgenerator.services.header_canvas import NumberedCanvas, fit_patient_header


class LastPageSignature(Flowable):
    """Custom flowable that only renders on the last page"""

    def __init__(self, doctor_info, styles):
        self.doctor_info = doctor_info
        self.styles = styles
        self.width = 0
        self.height = 120  # Approximate height needed for signature section

    def draw(self):
        """Draw the full signature section."""

    def wrap(self, availWidth, availHeight):
        """Return the space needed by this flowable"""
        return (self.width, self.height)


class HospitalLetterheadGenerator:
    """
    Base PDF generator with hospital letterhead template.
    Provides A4 portrait layout with header, footer, and pagination.
    """

    def __init__(self):
        self.page_size = A4
        self.hospital_config = settings.HOSPITAL_CONFIG
        self.pdf_config = settings.PDF_CONFIG
        self.margins = self._get_margins()
        self.styles = self._create_styles()

    def _get_margins(self):
        """Get page margins from configuration"""
        margins = self.pdf_config["margins"]
        return {
            "top": margins["top"] * cm,
            "bottom": margins["bottom"] * cm,
            "left": margins["left"] * cm,
            "right": margins["right"] * cm,
        }

    def _create_styles(self):
        """Create custom paragraph styles for medical documents"""
        styles = getSampleStyleSheet()

        # Hospital header style
        styles.add(
            ParagraphStyle(
                name="HospitalName",
                parent=styles["Title"],
                fontSize=16,
                textColor=darkblue,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=6,
                fontName="Times-Bold",
            )
        )

        styles.add(
            ParagraphStyle(
                name="HospitalDetails",
                parent=styles["Normal"],
                fontSize=10,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=12,
                fontName="Times-Roman",
            )
        )

        # Document title style
        styles.add(
            ParagraphStyle(
                name="DocumentTitle",
                parent=styles["Title"],
                fontSize=14,
                textColor=black,
                alignment=TA_CENTER,
                spaceBefore=12,
                spaceAfter=18,
                fontName="Times-Bold",
            )
        )

        # Patient info style
        styles.add(
            ParagraphStyle(
                name="PatientInfo",
                parent=styles["Normal"],
                fontSize=10,
                alignment=TA_LEFT,
                spaceBefore=6,
                spaceAfter=6,
                fontName="Times-Roman",
            )
        )

        # Content styles
        styles.add(
            ParagraphStyle(
                name="MedicalContent",
                parent=styles["Normal"],
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceBefore=6,
                spaceAfter=6,
                fontName="Times-Roman",
                leading=14,
            )
        )

        styles.add(
            ParagraphStyle(
                name="MedicalContentBold",
                parent=styles["MedicalContent"],
                fontName="Times-Bold",
            )
        )

        # Signature style
        styles.add(
            ParagraphStyle(
                name="Signature",
                parent=styles["Normal"],
                fontSize=10,
                alignment=TA_CENTER,
                spaceBefore=24,
                spaceAfter=6,
                fontName="Times-Roman",
            )
        )

        # Footer style
        styles.add(
            ParagraphStyle(
                name="Footer",
                parent=styles["Normal"],
                fontSize=9,
                alignment=TA_CENTER,
                fontName="Times-Roman",
                textColor=colors.grey,
            )
        )

        return styles

    def _create_patient_info_table(self, patient_data):
        """Create simplified patient information table (patient name is now in header)"""
        # Patient name is now in header on every page, so we can remove this table
        # or keep it minimal if needed for other information in the future
        return []

    def _create_signature_section(self, doctor_info):
        """Create medical signature section"""
        content = []
        # content.append(Spacer(1, 24))
        content.append(Spacer(1, 12))

        # Date and location line with auto-filled current date
        current_date = timezone.localtime().strftime("%d/%m/%Y")
        content.append(
            Paragraph(
                f"Data: {current_date} &nbsp;&nbsp;&nbsp;&nbsp; Local: Salvador - BA",
                self.styles["PatientInfo"],
            )
        )
        # content.append(Spacer(1, 12))

        # Signature line
        content.append(Paragraph("_" * 60, self.styles["Signature"]))

        # Doctor info
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

        # Format CRM field - show registration number if available, otherwise show blank line
        crm_field = registration_number if registration_number else "_______________"

        content.append(
            Paragraph(
                f"<b>{doctor_name}</b><br/>{profession} - CRM: {crm_field}<br/><b>Assinatura e Carimbo</b>",
                self.styles["Signature"],
            )
        )

        return content

    def generate_pdf(
        self,
        content_elements,
        document_title="Document",
        patient_data=None,
        doctor_info=None,
        canvasmaker=None,
        header_height_cm=None,
    ):
        """
        Generate PDF with hospital letterhead and content.

        Args:
            content_elements: List of ReportLab flowables (Paragraphs, Tables, etc.)
            document_title: Title of the document
            patient_data: Dict with patient information
            doctor_info: Dict with doctor information

        Returns:
            BytesIO buffer with PDF content
        """
        buffer = io.BytesIO()

        # Create document with custom canvas for headers/footers
        doc = BaseDocTemplate(buffer, pagesize=self.page_size, title=document_title)

        # Create frame for content area (leaving space for header and footer)
        # Header space: caller can override, otherwise use default sizing
        if header_height_cm is not None:
            header_space = header_height_cm * cm
        elif canvasmaker is None and patient_data and patient_data.get("name"):
            header_space = (
                fit_patient_header(patient_data["name"]).header_height_cm * cm
            )
        elif patient_data and patient_data.get("name"):
            header_space = 2.4 * cm
        else:
            header_space = 2 * cm
        content_frame = Frame(
            self.margins["left"],
            self.margins["bottom"] + 1 * cm,  # Extra space for footer
            self.page_size[0] - self.margins["left"] - self.margins["right"],
            self.page_size[1]
            - self.margins["top"]
            - self.margins["bottom"]
            - header_space,  # Space for header and footer
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
            id="content",
        )

        # Create page template with header and footer
        page_template = PageTemplate(
            id="letterhead",
            frames=[content_frame],
            onPage=self._on_page,
            pagesize=self.page_size,
        )

        doc.addPageTemplates([page_template])

        # Build document content
        story = []

        # Document title
        if document_title:
            story.append(Paragraph(document_title, self.styles["DocumentTitle"]))
            # story.append(Spacer(1, 12))
            # story.append(Spacer(1, 5))

        # Patient information table
        if patient_data:
            story.extend(self._create_patient_info_table(patient_data))

        # Main content
        story.extend(content_elements)

        # Signature section - always add to story, but small signatures handled by canvas
        story.extend(self._create_signature_section(doctor_info))

        # Build PDF with custom canvas for headers/footers
        if canvasmaker is None:

            def canvasmaker(filename, **kwargs):
                return NumberedCanvas(
                    filename,
                    hospital_config=self.hospital_config,
                    patient_data=patient_data,
                    doctor_info=doctor_info,
                    **kwargs,
                )

        doc.build(story, canvasmaker=canvasmaker)

        # Return buffer
        buffer.seek(0)
        return buffer

    def _on_page(self, canvas, doc):
        """Called for each page; headers and footers use NumberedCanvas."""

    def create_prescription_pdf(
        self, prescription_data, items, patient_data, doctor_info
    ):
        """
        Create a prescription PDF with specific formatting.

        Args:
            prescription_data: Dict with prescription information
            items: List of prescription items
            patient_data: Dict with patient information
            doctor_info: Dict with doctor information

        Returns:
            BytesIO buffer with PDF content
        """
        content = []

        # General instructions (before drug list)
        if prescription_data.get("instructions"):
            # Keep general instructions together as a section
            instructions_content = [
                Paragraph(
                    "<b>INSTRUÇÕES GERAIS:</b>", self.styles["MedicalContentBold"]
                ),
                Paragraph(
                    prescription_data["instructions"], self.styles["MedicalContent"]
                ),
            ]
            content.append(KeepTogether(instructions_content))

        # Prescription items
        if items:
            # content.append(
            #     Paragraph(
            #         "<b>MEDICAMENTOS PRESCRITOS:</b>", self.styles["MedicalContentBold"]
            #     )
            # )
            content.append(Spacer(1, 6))

            for i, item in enumerate(items, 1):
                # First line: drug_name presentation quantity
                first_line_parts = [
                    f"<b>{i}. {item.get('drug_name', '').capitalize()}</b>"
                ]

                if item.get("presentation"):
                    first_line_parts.append(f"- <i>{item['presentation']}</i>")

                if item.get("quantity"):
                    first_line_parts.append(f"- {item['quantity']}")

                first_line = " ".join(first_line_parts)

                # Second line: usage instructions (if present)
                item_content = [first_line]
                if item.get("usage_instructions"):
                    item_content.append(f"<b>Uso:</b> {item['usage_instructions']}")

                # Wrap each drug item in KeepTogether to prevent page splits
                drug_paragraph = Paragraph(
                    "<br/>".join(item_content), self.styles["MedicalContent"]
                )
                drug_spacer = Spacer(1, 8)

                # Keep drug info together on same page
                content.append(KeepTogether([drug_paragraph, drug_spacer]))

        return self.generate_pdf(
            content_elements=content,
            document_title="RECEITA MÉDICA",
            patient_data=patient_data,
            doctor_info=doctor_info,
        )
