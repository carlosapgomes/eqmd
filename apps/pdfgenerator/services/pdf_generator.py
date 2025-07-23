"""
Base PDF generation service with hospital letterhead template.
"""

import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black, darkblue, grey
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    BaseDocTemplate,
    PageTemplate,
    Frame,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import PageBreakIfNotEmpty
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from django.conf import settings
from django.contrib.staticfiles.finders import find


class NumberedCanvas(canvas.Canvas):
    """Custom canvas class for page numbering and headers/footers"""

    def __init__(self, *args, **kwargs):
        self.hospital_config = kwargs.pop("hospital_config", {})
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.page_count = 0

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for page_num, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self.draw_page_number(page_num + 1, num_pages)
            self.draw_header()
            self.draw_footer()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, num_pages):
        """Draw page number at bottom right"""
        self.setFont("Times-Roman", 9)
        self.setFillColor(grey)
        self.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Página {page_num}/{num_pages}")

    def draw_header(self):
        """Draw hospital header on each page"""
        # Draw hospital logo if available
        logo_path = self._get_logo_path()
        if logo_path and os.path.exists(logo_path):
            try:
                self.drawImage(
                    logo_path,
                    2 * cm,
                    A4[1] - 2.5 * cm,
                    width=2 * cm,
                    height=1.5 * cm,
                    preserveAspectRatio=True,
                )
            except Exception:
                pass  # If logo fails to load, continue without it

        # Draw hospital name
        hospital_name = self.hospital_config.get("name", "Medical Center")
        self.setFont("Times-Bold", 20)
        # self.setFillColor(darkblue)
        self.setFillColor(black)
        self.drawString(6 * cm, A4[1] - 2.0 * cm, hospital_name)

        # Draw hospital details
        # details = []
        # if self.hospital_config.get('address'):
        #     details.append(self.hospital_config['address'])
        # if self.hospital_config.get('phone'):
        #     details.append(f"Tel: {self.hospital_config['phone']}")
        # if self.hospital_config.get('email'):
        #     details.append(f"Email: {self.hospital_config['email']}")
        #
        # if details:
        #     details_text = " | ".join(details)
        #     self.setFont("Times-Roman", 10)
        #     self.setFillColor(black)
        #     self.drawString(5*cm, A4[1] - 2*cm, details_text)

        # Draw separator line
        self.setStrokeColor(black)
        self.setLineWidth(1)
        self.line(2 * cm, A4[1] - 2.8 * cm, A4[0] - 2 * cm, A4[1] - 2.8 * cm)

    def draw_footer(self):
        """Draw hospital footer on each page"""
        # Footer text
        footer_text = self.hospital_config.get("name", "Medical Center")
        if self.hospital_config.get("address"):
            footer_text += f" - {self.hospital_config['address']}"

        self.setFont("Times-Roman", 9)
        self.setFillColor(grey)
        self.drawCentredString(A4[0] / 2, 2 * cm, footer_text)

        # Footer line
        self.setStrokeColor(grey)
        self.setLineWidth(0.5)
        self.line(2 * cm, 2.5 * cm, A4[0] - 2 * cm, 2.5 * cm)

    def _get_logo_path(self):
        """Get the path to the hospital logo"""
        # Try logo_path first (local file path)
        if self.hospital_config.get("logo_path"):
            logo_path = self.hospital_config["logo_path"]
            # Try as static file first
            static_path = find(logo_path.replace("static/", ""))
            if static_path and os.path.exists(static_path):
                return static_path
            # Try as absolute path
            if os.path.exists(logo_path):
                return logo_path

        # Try logo_url (not implemented for security reasons - would need to download)
        return None


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
        """Create patient information table"""
        if not patient_data:
            return []

        # Patient info data
        data = [
            ["Nome do Paciente:", patient_data.get("name", "—")],
            ["CPF:", patient_data.get("fiscal_number", "—")],
            ["Data de Nascimento:", patient_data.get("birth_date", "—")],
            ["Cartão SUS:", patient_data.get("health_card_number", "—")],
        ]

        # Create table
        table = Table(data, colWidths=[4 * cm, 12 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),  # Bold labels
                ]
            )
        )

        return [table, Spacer(1, 12)]

    def _create_signature_section(self, doctor_info):
        """Create medical signature section"""
        content = []
        content.append(Spacer(1, 24))

        # Date and location line
        content.append(
            Paragraph(
                "Data: ___/___/______ &nbsp;&nbsp;&nbsp;&nbsp; Local: _________________________",
                self.styles["PatientInfo"],
            )
        )
        content.append(Spacer(1, 12))

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

        content.append(
            Paragraph(
                f"<b>{doctor_name}</b><br/>{profession} - CRM: _______________<br/><b>Assinatura e Carimbo</b>",
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
        content_frame = Frame(
            self.margins["left"],
            self.margins["bottom"] + 1 * cm,  # Extra space for footer
            self.page_size[0] - self.margins["left"] - self.margins["right"],
            self.page_size[1]
            - self.margins["top"]
            - self.margins["bottom"]
            - 2 * cm,  # Space for header and footer
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
            story.append(Spacer(1, 12))

        # Patient information table
        if patient_data:
            story.extend(self._create_patient_info_table(patient_data))

        # Main content
        story.extend(content_elements)

        # Signature section
        story.extend(self._create_signature_section(doctor_info))

        # Build PDF with custom canvas for headers/footers
        def canvas_maker(filename, **kwargs):
            return NumberedCanvas(
                filename, hospital_config=self.hospital_config, **kwargs
            )

        doc.build(story, canvasmaker=canvas_maker)

        # Return buffer
        buffer.seek(0)
        return buffer

    def _on_page(self, canvas, doc):
        """Called for each page - headers and footers are handled by NumberedCanvas"""
        pass  # Headers and footers are handled by the NumberedCanvas class

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

        # Prescription items
        if items:
            content.append(
                Paragraph(
                    "<b>MEDICAMENTOS PRESCRITOS:</b>", self.styles["MedicalContentBold"]
                )
            )
            content.append(Spacer(1, 6))

            for i, item in enumerate(items, 1):
                item_content = [f"<b>{i}. {item.get('drug_name', '')}</b>"]

                if item.get("presentation"):
                    item_content.append(f"<i>{item['presentation']}</i>")

                if item.get("usage_instructions"):
                    item_content.append(f"<b>Uso:</b> {item['usage_instructions']}")

                if item.get("quantity"):
                    item_content.append(f"<b>Quantidade:</b> {item['quantity']}")

                content.append(
                    Paragraph("<br/>".join(item_content), self.styles["MedicalContent"])
                )
                content.append(Spacer(1, 8))

        # General instructions
        if prescription_data.get("instructions"):
            content.append(Spacer(1, 12))
            content.append(
                Paragraph(
                    "<b>INSTRUÇÕES GERAIS:</b>", self.styles["MedicalContentBold"]
                )
            )
            content.append(Spacer(1, 6))
            content.append(
                Paragraph(
                    prescription_data["instructions"], self.styles["MedicalContent"]
                )
            )

        return self.generate_pdf(
            content_elements=content,
            document_title="RECEITA MÉDICA",
            patient_data=patient_data,
            doctor_info=doctor_info,
        )

