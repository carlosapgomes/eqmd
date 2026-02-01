from html import escape
import re

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator
from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser
from apps.dischargereports.utils import clean_text_field


class DischargeReportPDFGenerator(HospitalLetterheadGenerator):
    """PDF generator for discharge reports using hospital letterhead layout."""

    def __init__(self):
        super().__init__()
        self.markdown_parser = MarkdownToPDFParser(self.styles)

    def _format_date(self, value):
        if not value:
            return "—"
        return value.strftime("%d/%m/%Y")

    def _format_duration(self, admission_date, discharge_date):
        if not admission_date or not discharge_date:
            return "—"
        days = (discharge_date - admission_date).days
        return f"{days} dias" if days != 1 else "1 dia"

    def _build_patient_info(self, report):
        patient = report.patient
        record_number = patient.get_current_record_number() or "—"
        birth_date = self._format_date(patient.birthday)
        gender = patient.get_gender_display() if getattr(patient, "gender", None) else "—"
        age = f"{patient.age} anos" if getattr(patient, "age", None) is not None else "—"
        admission_date = self._format_date(report.admission_date)
        discharge_date = self._format_date(report.discharge_date)
        permanence = self._format_duration(report.admission_date, report.discharge_date)
        fields = [
            ("Nome", patient.name),
            ("Prontuário", record_number),
            ("Idade", age),
            ("Data de Nascimento", birth_date),
            ("Gênero", gender),
            ("Data de Admissão", admission_date),
            ("Data de Alta", discharge_date),
            ("Permanência", permanence),
        ]

        if report.medical_specialty:
            fields.insert(2, ("Especialidade", report.medical_specialty))

        table_rows = []
        for index in range(0, len(fields), 2):
            row_fields = fields[index:index + 2]
            row = []
            for label, value in row_fields:
                cell_text = f"<b>{escape(str(label))}:</b> {escape(str(value))}"
                row.append(Paragraph(cell_text, self.styles["PatientInfo"]))
            if len(row) == 1:
                row.append(Paragraph("", self.styles["PatientInfo"]))
            table_rows.append(row)

        available_width = (
            self.page_size[0] - self.margins["left"] - self.margins["right"]
        )
        table = Table(table_rows, colWidths=[available_width / 2] * 2)
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ]
            )
        )

        heading = Paragraph(
            "<b>Identificação do Paciente</b>", self.styles["MedicalContentBold"]
        )
        content = [Spacer(1, 12), heading, Spacer(1, 6), table, Spacer(1, 12)]
        return [KeepTogether(content)]

    def _add_section(self, content_elements, title, value):
        if not value:
            return
        cleaned = clean_text_field(value)
        section_markdown = f"## {title}\n\n{cleaned}"
        content_elements.extend(self.markdown_parser.parse(section_markdown))

    def _compact_flowables(self, flowables):
        compact = []
        for flowable in flowables:
            if isinstance(flowable, Spacer):
                height = getattr(flowable, "height", None)
                if height is None:
                    height = getattr(flowable, "h", None)
                if height is None:
                    compact.append(flowable)
                    continue
                new_height = max(2, min(height * 0.5, 4))
                if compact and isinstance(compact[-1], Spacer):
                    last_height = getattr(compact[-1], "height", 0)
                    compact[-1] = Spacer(1, max(last_height, new_height))
                else:
                    compact.append(Spacer(1, new_height))
            else:
                compact.append(flowable)
        while compact and isinstance(compact[0], Spacer):
            compact.pop(0)
        while compact and isinstance(compact[-1], Spacer):
            compact.pop()
        return compact

    def _add_compact_section(self, content_elements, title, value):
        if not value:
            return
        cleaned = clean_text_field(value)
        heading = Paragraph(
            f"<b>{escape(str(title))}</b>", self.styles["MedicalContentBold"]
        )
        content_elements.append(Spacer(1, 8))
        content_elements.append(heading)
        content_elements.append(Spacer(1, 4))
        body_flowables = self.markdown_parser.parse(cleaned)
        content_elements.extend(self._compact_flowables(body_flowables))
        content_elements.append(Spacer(1, 4))

    def _extract_list_lines(self, value):
        if not value:
            return []
        text = value.replace("\r\n", "\n").replace("\r", "\n")
        lines = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^(\d+[.)]|\-|\*|•)\s+", "", line)
            lines.append(line)
        return lines

    def _add_compact_list_section(self, content_elements, title, value):
        lines = self._extract_list_lines(value)
        if not lines:
            return

        heading = Paragraph(
            f"<b>{escape(str(title))}</b>", self.styles["MedicalContentBold"]
        )
        content_elements.append(Spacer(1, 8))
        content_elements.append(heading)
        content_elements.append(Spacer(1, 4))

        compact_style = self.styles["MedicalContent"].clone("CompactListItem")
        compact_style.spaceBefore = 0
        compact_style.spaceAfter = 0
        compact_style.leading = 12

        bullet_style = self.styles["PatientInfo"].clone("CompactListBullet")
        bullet_style.spaceBefore = 0
        bullet_style.spaceAfter = 0

        table_rows = [
            [
                Paragraph("•", bullet_style),
                Paragraph(escape(str(line)), compact_style),
            ]
            for line in lines
        ]

        available_width = (
            self.page_size[0] - self.margins["left"] - self.margins["right"]
        )
        bullet_width = 0.45 * cm
        table = Table(
            table_rows, colWidths=[bullet_width, available_width - bullet_width]
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (0, -1), 0),
                    ("RIGHTPADDING", (0, 0), (0, -1), 4),
                    ("LEFTPADDING", (1, 0), (1, -1), 0),
                    ("RIGHTPADDING", (1, 0), (1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        content_elements.append(table)
        content_elements.append(Spacer(1, 4))

    def generate_from_report(self, report):
        content_elements = []

        content_elements.extend(self._build_patient_info(report))

        self._add_compact_list_section(
            content_elements, "Problemas e Diagnósticos", report.problems_and_diagnosis
        )
        self._add_compact_section(
            content_elements, "História da Admissão", report.admission_history
        )
        self._add_compact_section(
            content_elements, "Lista de Exames", report.exams_list
        )
        self._add_compact_section(
            content_elements, "Lista de Procedimentos", report.procedures_list
        )
        self._add_compact_section(
            content_elements, "História Médica da Internação", report.inpatient_medical_history
        )
        self._add_compact_section(
            content_elements, "Status da Alta", report.discharge_status
        )
        self._add_compact_section(
            content_elements, "Recomendações de Alta", report.discharge_recommendations
        )

        patient_data = {
            "name": report.patient.name,
        }

        doctor = report.created_by
        doctor_info = {
            "name": doctor.get_full_name() or doctor.username,
            "profession": getattr(doctor, "profession", "Médico"),
            "registration_number": getattr(doctor, "professional_registration_number", ""),
        }

        return self.generate_pdf(
            content_elements=content_elements,
            document_title="RELATÓRIO DE ALTA",
            patient_data=patient_data,
            doctor_info=doctor_info,
        )
