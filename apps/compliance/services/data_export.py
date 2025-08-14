import json
import csv
from datetime import datetime
from io import StringIO, BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


class PatientDataExportService:
    """Service to export patient data in various formats for LGPD compliance"""

    def __init__(self, patient):
        self.patient = patient

    def export_data(self, format_type='pdf', request_id=None):
        """Export patient data in specified format"""

        data = self.collect_patient_data()

        if format_type == 'json':
            return self.export_as_json(data, request_id)
        elif format_type == 'csv':
            return self.export_as_csv(data, request_id)
        elif format_type == 'pdf':
            return self.export_as_pdf(data, request_id)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def collect_patient_data(self):
        """Collect all patient data for export"""

        # Basic patient information
        patient_data = {
            'identificacao': {
                'nome': self.patient.name,
                'data_nascimento': self.patient.birthday.strftime('%d/%m/%Y') if self.patient.birthday else None,
                'cpf': getattr(self.patient, 'id_number', None),
                'cartao_sus': getattr(self.patient, 'healthcard_number', None),
                'genero': self.patient.get_gender_display() if hasattr(self.patient, 'gender') else None,
                'telefone': getattr(self.patient, 'phone', None),
                'endereco': {
                    'endereco': getattr(self.patient, 'address', None),
                    'cidade': getattr(self.patient, 'city', None),
                    'estado': getattr(self.patient, 'state', None),
                    'cep': getattr(self.patient, 'zip_code', None),
                }
            },
            'dados_hospitalares': {
                'data_admissao': self.patient.admission_date.strftime('%d/%m/%Y %H:%M') if self.patient.admission_date else None,
                'data_alta': self.patient.discharge_date.strftime('%d/%m/%Y %H:%M') if self.patient.discharge_date else None,
                'status': self.patient.get_status_display(),
                'enfermaria': self.patient.ward.name if self.patient.ward else None,
                'tags': [tag.name for tag in self.patient.tags.all()],
            },
            'historico_medico': [],
            'evolucoes_diarias': [],
            'midias_anexas': [],
            'formularios_pdf': [],
        }

        # Medical events
        if hasattr(self.patient, 'events'):
            for event in self.patient.events.all().order_by('created_at'):
                event_data = {
                    'id': str(event.id),
                    'tipo': event.__class__.__name__,
                    'data_criacao': event.created_at.strftime('%d/%m/%Y %H:%M'),
                    'data_atualizacao': event.updated_at.strftime('%d/%m/%Y %H:%M'),
                    'autor': event.author.get_full_name() if event.author else None,
                }

                # Add specific event data based on type
                if hasattr(event, 'content'):
                    event_data['conteudo'] = event.content

                patient_data['historico_medico'].append(event_data)

        # Daily notes
        if hasattr(self.patient, 'dailynotes'):
            for note in self.patient.dailynotes.all().order_by('created_at'):
                note_data = {
                    'id': str(note.id),
                    'data': note.created_at.strftime('%d/%m/%Y %H:%M'),
                    'autor': note.author.get_full_name() if note.author else None,
                    'conteudo': note.content if hasattr(note, 'content') else None,
                }
                patient_data['evolucoes_diarias'].append(note_data)

        # Media files
        if hasattr(self.patient, 'mediafiles'):
            for media in self.patient.mediafiles.all():
                media_data = {
                    'id': str(media.id),
                    'nome_arquivo': media.file.name if media.file else None,
                    'tipo': media.file_type if hasattr(media, 'file_type') else None,
                    'data_upload': media.created_at.strftime('%d/%m/%Y %H:%M'),
                    'tamanho_bytes': media.file.size if media.file else None,
                }
                patient_data['midias_anexas'].append(media_data)

        return patient_data

    def export_as_json(self, data, request_id):
        """Export data as JSON file"""

        export_metadata = {
            'exportado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'solicitacao_id': request_id,
            'formato': 'JSON',
            'observacao': 'Dados exportados conforme LGPD Art. 18'
        }

        complete_data = {
            'metadata': export_metadata,
            'dados_paciente': data
        }

        response = HttpResponse(
            json.dumps(complete_data, ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="dados_paciente_{request_id}.json"'
        return response

    def export_as_csv(self, data, request_id):
        """Export data as CSV file"""

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Categoria', 'Campo', 'Valor'])

        # Patient identification
        for key, value in data['identificacao'].items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    writer.writerow(['Identificação', f"{key}.{subkey}", subvalue or ''])
            else:
                writer.writerow(['Identificação', key, value or ''])

        # Hospital data
        for key, value in data['dados_hospitalares'].items():
            if isinstance(value, list):
                writer.writerow(['Dados Hospitalares', key, ', '.join(value)])
            else:
                writer.writerow(['Dados Hospitalares', key, value or ''])

        # Medical history
        for i, event in enumerate(data['historico_medico']):
            for key, value in event.items():
                writer.writerow(['Histórico Médico', f"evento_{i}.{key}", value or ''])

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="dados_paciente_{request_id}.csv"'
        return response

    def export_as_pdf(self, data, request_id):
        """Export data as PDF file"""

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph('Dados do Paciente - LGPD', title_style))
        story.append(Spacer(1, 12))

        # Metadata
        story.append(Paragraph(f'<b>Solicitação:</b> {request_id}', styles['Normal']))
        story.append(Paragraph(f'<b>Exportado em:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal']))
        story.append(Paragraph('<b>Base Legal:</b> LGPD Art. 18 - Direito de Acesso', styles['Normal']))
        story.append(Spacer(1, 20))

        # Patient identification
        story.append(Paragraph('<b>DADOS DE IDENTIFICAÇÃO</b>', styles['Heading2']))

        id_data = [
            ['Campo', 'Valor'],
            ['Nome', data['identificacao']['nome'] or ''],
            ['Data de Nascimento', data['identificacao']['data_nascimento'] or ''],
            ['CPF', data['identificacao']['cpf'] or ''],
            ['Cartão SUS', data['identificacao']['cartao_sus'] or ''],
            ['Telefone', data['identificacao']['telefone'] or ''],
        ]

        id_table = Table(id_data)
        id_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(id_table)
        story.append(Spacer(1, 20))

        # Hospital data
        story.append(Paragraph('<b>DADOS HOSPITALARES</b>', styles['Heading2']))

        hospital_data = [
            ['Campo', 'Valor'],
            ['Data de Admissão', data['dados_hospitalares']['data_admissao'] or ''],
            ['Data de Alta', data['dados_hospitalares']['data_alta'] or ''],
            ['Status', data['dados_hospitalares']['status'] or ''],
            ['Enfermaria', data['dados_hospitalares']['enfermaria'] or ''],
            ['Tags', ', '.join(data['dados_hospitalares']['tags'])],
        ]

        hospital_table = Table(hospital_data)
        hospital_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(hospital_table)
        story.append(Spacer(1, 20))

        # Medical history summary
        if data['historico_medico']:
            story.append(Paragraph('<b>HISTÓRICO MÉDICO</b>', styles['Heading2']))
            story.append(Paragraph(f'Total de eventos registrados: {len(data["historico_medico"])}', styles['Normal']))

            for event in data['historico_medico'][:10]:  # Limit to first 10 events
                story.append(Paragraph(f'<b>{event["tipo"]}</b> - {event["data_criacao"]}', styles['Normal']))
                if event.get('conteudo'):
                    story.append(Paragraph(event['conteudo'][:200] + '...', styles['Italic']))
                story.append(Spacer(1, 6))

        # Footer note
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            '<i>Este documento contém dados pessoais protegidos pela LGPD. '
            'Seu uso deve respeitar os princípios de finalidade, adequação e necessidade.</i>',
            styles['Italic']
        ))

        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="dados_paciente_{request_id}.pdf"'
        return response