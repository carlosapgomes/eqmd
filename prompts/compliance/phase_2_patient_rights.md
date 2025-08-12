# Phase 2: Patient Rights System Implementation

**Timeline**: Week 3-4  
**Priority**: HIGH  
**Dependencies**: Phase 1 completed  

## Objective

Implement the core patient rights system required by LGPD Article 18, allowing patients to request access to their data, request corrections, and exercise other fundamental rights.

## Legal Requirements Addressed

- **LGPD Article 18**: Data subject rights (access, rectification, deletion, portability, objection)
- **LGPD Article 19**: Right to information about data sharing
- **LGPD Article 20**: Right to portability
- **LGPD Article 9**: Information to be provided to data subjects

## Deliverables

1. **Patient Data Request System**
2. **Data Access/Export Functionality**  
3. **Data Correction Request Workflow**
4. **Staff Request Management Interface**
5. **Patient Communication Templates**

---

## Implementation Steps

### Step 1: Patient Rights Models

#### 1.1 Patient Data Request Model

**File**: `apps/patients/models.py` (additions)

```python
from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid

class PatientDataRequest(models.Model):
    """Handles patient data rights requests - LGPD Article 18"""
    
    REQUEST_TYPES = [
        ('access', 'Acesso aos dados (Art. 18, I e II)'),
        ('correction', 'Correção de dados (Art. 18, III)'),
        ('deletion', 'Exclusão de dados (Art. 18, IV)'),
        ('portability', 'Portabilidade de dados (Art. 18, V)'),
        ('objection', 'Oposição ao tratamento (Art. 18, § 2º)'),
        ('information', 'Informações sobre compartilhamento (Art. 18, VII)'),
        ('consent_revocation', 'Revogação do consentimento (Art. 18, IX)'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('under_review', 'Em análise'),
        ('identity_verification', 'Verificação de identidade'),
        ('approved', 'Aprovado'),
        ('in_progress', 'Em andamento'),
        ('completed', 'Concluído'),
        ('rejected', 'Rejeitado'),
        ('cancelled', 'Cancelado'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]
    
    # Request identification
    request_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='data_requests', null=True, blank=True)
    
    # Request details
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    description = models.TextField(verbose_name="Descrição da solicitação")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    
    # Requester information (may be different from patient)
    requester_name = models.CharField(max_length=200, verbose_name="Nome do solicitante")
    requester_email = models.EmailField(verbose_name="Email para contato")
    requester_phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    requester_relationship = models.CharField(
        max_length=50, 
        choices=[
            ('self', 'Próprio paciente'),
            ('parent', 'Pai/Mãe'),
            ('guardian', 'Responsável legal'),
            ('attorney', 'Procurador'),
            ('heir', 'Herdeiro'),
        ],
        default='self',
        verbose_name="Relação com o paciente"
    )
    
    # Patient identification for matching
    patient_name_provided = models.CharField(max_length=200, verbose_name="Nome do paciente informado")
    patient_cpf_provided = models.CharField(max_length=14, blank=True, verbose_name="CPF informado")
    patient_birth_date_provided = models.DateField(null=True, blank=True, verbose_name="Data nascimento informada")
    additional_identifiers = models.TextField(blank=True, verbose_name="Outros identificadores")
    
    # Supporting documentation
    identity_document = models.FileField(
        upload_to='lgpd/identity_docs/',
        null=True, 
        blank=True,
        verbose_name="Documento de identidade"
    )
    authorization_document = models.FileField(
        upload_to='lgpd/authorization_docs/',
        null=True,
        blank=True,
        verbose_name="Procuração/autorização"
    )
    
    # Processing details
    requested_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(editable=False)  # Auto-calculated: 15 days from request
    
    # Staff processing
    assigned_to = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_data_requests',
        verbose_name="Responsável pelo atendimento"
    )
    reviewed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_data_requests',
        verbose_name="Revisado por"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Response details
    response_notes = models.TextField(blank=True, verbose_name="Notas da resposta")
    rejection_reason = models.TextField(blank=True, verbose_name="Motivo da rejeição")
    response_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Files and data
    response_file = models.FileField(
        upload_to='lgpd/responses/',
        null=True,
        blank=True,
        verbose_name="Arquivo de resposta"
    )
    data_export_format = models.CharField(
        max_length=10,
        choices=[('pdf', 'PDF'), ('json', 'JSON'), ('csv', 'CSV')],
        default='pdf',
        verbose_name="Formato de exportação"
    )
    
    # Compliance tracking
    legal_basis_for_rejection = models.CharField(max_length=100, blank=True)
    anpd_notification_sent = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Solicitação de Direitos do Titular"
        verbose_name_plural = "Solicitações de Direitos dos Titulares"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['patient', 'request_type']),
            models.Index(fields=['requester_email', 'requested_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = self.generate_request_id()
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=15)
        super().save(*args, **kwargs)
    
    def generate_request_id(self):
        """Generate unique request ID: REQ-YYYYMMDD-XXXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        sequence = PatientDataRequest.objects.filter(
            request_id__startswith=f'REQ-{date_str}'
        ).count() + 1
        return f'REQ-{date_str}-{sequence:04d}'
    
    def is_overdue(self):
        """Check if request is overdue (LGPD requires response within reasonable time)"""
        return timezone.now() > self.due_date and self.status not in ['completed', 'rejected', 'cancelled']
    
    def days_remaining(self):
        """Days remaining to comply with request"""
        if self.status in ['completed', 'rejected', 'cancelled']:
            return 0
        remaining = (self.due_date - timezone.now()).days
        return max(0, remaining)
    
    def __str__(self):
        return f"{self.request_id} - {self.get_request_type_display()} - {self.requester_name}"
```

#### 1.2 Data Correction Request Detail Model

```python
class DataCorrectionDetail(models.Model):
    """Detailed correction requests for specific data fields"""
    
    request = models.ForeignKey(PatientDataRequest, on_delete=models.CASCADE, related_name='correction_details')
    field_name = models.CharField(max_length=100, verbose_name="Campo a corrigir")
    current_value = models.TextField(verbose_name="Valor atual")
    requested_value = models.TextField(verbose_name="Valor solicitado")
    justification = models.TextField(verbose_name="Justificativa para correção")
    
    # Staff review
    approved = models.BooleanField(null=True, blank=True)
    review_notes = models.TextField(blank=True, verbose_name="Notas da revisão")
    reviewed_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Implementation
    correction_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_corrections'
    )
    
    class Meta:
        verbose_name = "Detalhe de Correção"
        verbose_name_plural = "Detalhes de Correção"
```

### Step 2: Patient Request Forms

#### 2.1 Public Request Form

**File**: `apps/patients/forms.py` (additions)

```python
from django import forms
from .models import PatientDataRequest, DataCorrectionDetail
from django.core.exceptions import ValidationError
import re

class PatientDataRequestForm(forms.ModelForm):
    """Public form for patients to submit data requests"""
    
    # Additional field for verification
    verify_email = forms.EmailField(
        label="Confirme seu email",
        help_text="Digite novamente seu email para confirmação"
    )
    
    terms_accepted = forms.BooleanField(
        label="Li e aceito os termos",
        help_text="Declaro que li e compreendo como meus dados serão processados para atender esta solicitação",
        required=True
    )
    
    class Meta:
        model = PatientDataRequest
        fields = [
            'request_type', 'description', 'requester_name', 'requester_email',
            'requester_phone', 'requester_relationship', 'patient_name_provided',
            'patient_cpf_provided', 'patient_birth_date_provided', 'additional_identifiers',
            'identity_document', 'authorization_document', 'data_export_format'
        ]
        
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Descreva detalhadamente sua solicitação...',
                'class': 'form-control'
            }),
            'requester_name': forms.TextInput(attrs={'class': 'form-control'}),
            'requester_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'requester_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(11) 99999-9999'}),
            'requester_relationship': forms.Select(attrs={'class': 'form-select'}),
            'patient_name_provided': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_cpf_provided': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'patient_birth_date_provided': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'additional_identifiers': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Ex: Cartão SUS, data da última consulta, médico responsável...',
                'class': 'form-control'
            }),
            'data_export_format': forms.Select(attrs={'class': 'form-select'}),
        }
        
        labels = {
            'request_type': 'Tipo de Solicitação',
            'description': 'Descrição da Solicitação',
            'requester_name': 'Seu Nome Completo',
            'requester_email': 'Seu Email',
            'requester_phone': 'Telefone (opcional)',
            'requester_relationship': 'Sua Relação com o Paciente',
            'patient_name_provided': 'Nome do Paciente',
            'patient_cpf_provided': 'CPF do Paciente (opcional)',
            'patient_birth_date_provided': 'Data de Nascimento do Paciente',
            'additional_identifiers': 'Informações Adicionais para Identificação',
            'identity_document': 'Documento de Identidade (obrigatório)',
            'authorization_document': 'Procuração (se aplicável)',
            'data_export_format': 'Formato Preferido para Dados',
        }
        
        help_texts = {
            'request_type': 'Selecione o tipo de direito que deseja exercer conforme LGPD',
            'description': 'Forneça detalhes específicos sobre o que você está solicitando',
            'patient_cpf_provided': 'Opcional, mas ajuda na identificação',
            'additional_identifiers': 'Qualquer informação que ajude a identificar o paciente',
            'identity_document': 'Anexe cópia de documento oficial com foto para verificação',
            'authorization_document': 'Necessário apenas se você não for o próprio paciente',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Email confirmation
        email = cleaned_data.get('requester_email')
        verify_email = cleaned_data.get('verify_email')
        if email and verify_email and email != verify_email:
            raise ValidationError("Os emails não conferem.")
        
        # Validate CPF format if provided
        cpf = cleaned_data.get('patient_cpf_provided')
        if cpf:
            cpf_clean = re.sub(r'[^\d]', '', cpf)
            if len(cpf_clean) != 11:
                raise ValidationError({'patient_cpf_provided': 'CPF deve ter 11 dígitos'})
        
        # Require authorization document for non-self requests
        relationship = cleaned_data.get('requester_relationship')
        auth_doc = cleaned_data.get('authorization_document')
        if relationship != 'self' and not auth_doc:
            raise ValidationError({
                'authorization_document': 'Procuração é obrigatória quando não é o próprio paciente'
            })
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and enhance form appearance
        for field_name, field in self.fields.items():
            if field_name not in ['terms_accepted']:
                field.widget.attrs.update({'class': 'form-control'})
```

#### 2.2 Staff Request Management Form

```python
class PatientDataRequestManagementForm(forms.ModelForm):
    """Staff form for managing patient data requests"""
    
    class Meta:
        model = PatientDataRequest
        fields = [
            'status', 'assigned_to', 'priority', 'response_notes',
            'rejection_reason', 'legal_basis_for_rejection'
        ]
        
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'response_notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'rejection_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'legal_basis_for_rejection': forms.TextInput(attrs={'class': 'form-control'}),
        }
```

### Step 3: Data Export Functionality

#### 3.1 Patient Data Export Service

**File**: `apps/patients/services/data_export.py`

```python
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
```

### Step 4: Views and URLs

#### 4.1 Patient Request Views

**File**: `apps/patients/views.py` (additions)

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404
from django.views.generic import CreateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .models import PatientDataRequest
from .forms import PatientDataRequestForm, PatientDataRequestManagementForm
from .services.data_export import PatientDataExportService

class PatientDataRequestCreateView(CreateView):
    """Public view for patients to submit data requests"""
    model = PatientDataRequest
    form_class = PatientDataRequestForm
    template_name = 'patients/data_request_form.html'
    success_url = '/lgpd/solicitacao/confirmacao/'
    
    def form_valid(self, form):
        # Save the request
        response = super().form_valid(form)
        
        # Send confirmation email
        self.send_confirmation_email(self.object)
        
        # Notify staff
        self.notify_staff_new_request(self.object)
        
        messages.success(
            self.request,
            f'Sua solicitação foi registrada com o número {self.object.request_id}. '
            'Você receberá uma resposta em até 15 dias.'
        )
        
        return response
    
    def send_confirmation_email(self, request_obj):
        """Send confirmation email to requester"""
        subject = f'Confirmação de Solicitação LGPD - {request_obj.request_id}'
        message = f"""
        Prezado(a) {request_obj.requester_name},
        
        Sua solicitação de dados foi registrada com sucesso:
        
        Número da Solicitação: {request_obj.request_id}
        Tipo: {request_obj.get_request_type_display()}
        Data da Solicitação: {request_obj.requested_at.strftime('%d/%m/%Y %H:%M')}
        Prazo para Resposta: {request_obj.due_date.strftime('%d/%m/%Y')}
        
        Descrição: {request_obj.description}
        
        Sua solicitação está sendo analisada por nossa equipe. Você receberá uma resposta
        no email {request_obj.requester_email} em até 15 dias conforme estabelecido pela LGPD.
        
        Para acompanhar o status da sua solicitação, guarde este número: {request_obj.request_id}
        
        Atenciosamente,
        Equipe de Proteção de Dados
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [request_obj.requester_email],
                fail_silently=True
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send confirmation email: {e}")
    
    def notify_staff_new_request(self, request_obj):
        """Notify staff about new data request"""
        from apps.core.models import LGPDComplianceSettings
        
        try:
            settings_obj = LGPDComplianceSettings.objects.first()
            if settings_obj and settings_obj.dpo_email:
                subject = f'Nova Solicitação LGPD - {request_obj.request_id}'
                message = f"""
                Nova solicitação de dados recebida:
                
                ID: {request_obj.request_id}
                Tipo: {request_obj.get_request_type_display()}
                Solicitante: {request_obj.requester_name}
                Email: {request_obj.requester_email}
                Paciente: {request_obj.patient_name_provided}
                Prazo: {request_obj.due_date.strftime('%d/%m/%Y')}
                
                Acesse o admin para revisar e processar a solicitação.
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings_obj.dpo_email],
                    fail_silently=True
                )
        except Exception as e:
            print(f"Failed to notify staff: {e}")

def patient_data_request_confirmation(request):
    """Confirmation page after request submission"""
    return render(request, 'patients/data_request_confirmation.html')

@login_required
def patient_data_export(request, request_id):
    """Export patient data for approved requests"""
    data_request = get_object_or_404(
        PatientDataRequest,
        request_id=request_id,
        status='approved'
    )
    
    if not data_request.patient:
        raise Http404("Patient not found for this request")
    
    # Check permissions (staff only)
    if not request.user.is_staff:
        raise Http404("Permission denied")
    
    # Export data
    export_service = PatientDataExportService(data_request.patient)
    response = export_service.export_data(
        format_type=data_request.data_export_format,
        request_id=request_id
    )
    
    # Update request status
    data_request.status = 'completed'
    data_request.response_sent_at = timezone.now()
    data_request.save()
    
    return response

class PatientDataRequestListView(LoginRequiredMixin, ListView):
    """Staff view to list and manage data requests"""
    model = PatientDataRequest
    template_name = 'admin/patients/data_request_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PatientDataRequest.objects.all()
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by overdue
        overdue = self.request.GET.get('overdue')
        if overdue == 'true':
            queryset = queryset.filter(due_date__lt=timezone.now())
        
        return queryset.order_by('-requested_at')

class PatientDataRequestDetailView(LoginRequiredMixin, DetailView):
    """Staff view to manage individual data requests"""
    model = PatientDataRequest
    template_name = 'admin/patients/data_request_detail.html'
    context_object_name = 'data_request'
    
    def get_object(self):
        return get_object_or_404(PatientDataRequest, request_id=self.kwargs['request_id'])
```

#### 4.2 URL Configuration

**File**: `apps/patients/urls.py` (additions)

```python
from django.urls import path
from . import views

# Add these to existing urlpatterns
urlpatterns += [
    # Public LGPD request URLs
    path('lgpd/solicitacao/', views.PatientDataRequestCreateView.as_view(), name='patient_data_request'),
    path('lgpd/solicitacao/confirmacao/', views.patient_data_request_confirmation, name='patient_data_request_confirmation'),
    
    # Staff management URLs
    path('admin/lgpd/solicitacoes/', views.PatientDataRequestListView.as_view(), name='data_request_list'),
    path('admin/lgpd/solicitacao/<str:request_id>/', views.PatientDataRequestDetailView.as_view(), name='data_request_detail'),
    path('admin/lgpd/export/<str:request_id>/', views.patient_data_export, name='patient_data_export'),
]
```

### Step 5: Templates

#### 5.1 Public Request Form Template

**File**: `apps/patients/templates/patients/data_request_form.html`

```html
{% extends "base.html" %}
{% load static %}
{% load widget_tweaks %}

{% block title %}Solicitação de Dados - LGPD{% endblock %}

{% block extra_css %}
<style>
.lgpd-header {
    background: linear-gradient(135deg, #2c3e50, #3498db);
    color: white;
    padding: 2rem 0;
}
.form-section {
    background: #f8f9fa;
    border-left: 4px solid #3498db;
    padding: 1rem;
    margin-bottom: 1.5rem;
}
.required-field::after {
    content: " *";
    color: #e74c3c;
}
</style>
{% endblock %}

{% block content %}
<div class="lgpd-header">
    <div class="container">
        <div class="row">
            <div class="col-md-8">
                <h1><i class="bi bi-shield-check me-3"></i>Solicitação de Dados Pessoais</h1>
                <p class="lead">Exercite seus direitos conforme a Lei Geral de Proteção de Dados (LGPD)</p>
            </div>
        </div>
    </div>
</div>

<div class="container mt-4">
    <div class="row">
        <div class="col-md-8">
            <div class="card shadow">
                <div class="card-header">
                    <h5><i class="bi bi-file-text me-2"></i>Formulário de Solicitação</h5>
                </div>
                <div class="card-body">
                    {% if messages %}
                        {% for message in messages %}
                            <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                    
                    <form method="post" enctype="multipart/form-data">
                        {% csrf_token %}
                        
                        <!-- Request Type Section -->
                        <div class="form-section">
                            <h6 class="text-primary mb-3">Tipo de Solicitação</h6>
                            
                            <div class="mb-3">
                                <label class="form-label required-field">{{ form.request_type.label }}</label>
                                {{ form.request_type|add_class:"form-select" }}
                                {% if form.request_type.help_text %}
                                    <div class="form-text">{{ form.request_type.help_text }}</div>
                                {% endif %}
                                {% for error in form.request_type.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                {% endfor %}
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label required-field">{{ form.description.label }}</label>
                                {{ form.description|add_class:"form-control" }}
                                {% if form.description.help_text %}
                                    <div class="form-text">{{ form.description.help_text }}</div>
                                {% endif %}
                                {% for error in form.description.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                {% endfor %}
                            </div>
                        </div>
                        
                        <!-- Requester Information Section -->
                        <div class="form-section">
                            <h6 class="text-primary mb-3">Seus Dados de Contato</h6>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label required-field">{{ form.requester_name.label }}</label>
                                    {{ form.requester_name|add_class:"form-control" }}
                                    {% for error in form.requester_name.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label required-field">{{ form.requester_relationship.label }}</label>
                                    {{ form.requester_relationship|add_class:"form-select" }}
                                    {% for error in form.requester_relationship.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label required-field">{{ form.requester_email.label }}</label>
                                    {{ form.requester_email|add_class:"form-control" }}
                                    {% for error in form.requester_email.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label required-field">{{ form.verify_email.label }}</label>
                                    {{ form.verify_email|add_class:"form-control" }}
                                    {% if form.verify_email.help_text %}
                                        <div class="form-text">{{ form.verify_email.help_text }}</div>
                                    {% endif %}
                                    {% for error in form.verify_email.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">{{ form.requester_phone.label }}</label>
                                {{ form.requester_phone|add_class:"form-control" }}
                                {% for error in form.requester_phone.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                {% endfor %}
                            </div>
                        </div>
                        
                        <!-- Patient Information Section -->
                        <div class="form-section">
                            <h6 class="text-primary mb-3">Identificação do Paciente</h6>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label required-field">{{ form.patient_name_provided.label }}</label>
                                    {{ form.patient_name_provided|add_class:"form-control" }}
                                    {% for error in form.patient_name_provided.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">{{ form.patient_birth_date_provided.label }}</label>
                                    {{ form.patient_birth_date_provided|add_class:"form-control" }}
                                    {% for error in form.patient_birth_date_provided.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">{{ form.patient_cpf_provided.label }}</label>
                                    {{ form.patient_cpf_provided|add_class:"form-control" }}
                                    {% if form.patient_cpf_provided.help_text %}
                                        <div class="form-text">{{ form.patient_cpf_provided.help_text }}</div>
                                    {% endif %}
                                    {% for error in form.patient_cpf_provided.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">{{ form.data_export_format.label }}</label>
                                    {{ form.data_export_format|add_class:"form-select" }}
                                    {% for error in form.data_export_format.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">{{ form.additional_identifiers.label }}</label>
                                {{ form.additional_identifiers|add_class:"form-control" }}
                                {% if form.additional_identifiers.help_text %}
                                    <div class="form-text">{{ form.additional_identifiers.help_text }}</div>
                                {% endif %}
                                {% for error in form.additional_identifiers.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                {% endfor %}
                            </div>
                        </div>
                        
                        <!-- Documents Section -->
                        <div class="form-section">
                            <h6 class="text-primary mb-3">Documentos</h6>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label required-field">{{ form.identity_document.label }}</label>
                                    {{ form.identity_document|add_class:"form-control" }}
                                    {% if form.identity_document.help_text %}
                                        <div class="form-text">{{ form.identity_document.help_text }}</div>
                                    {% endif %}
                                    {% for error in form.identity_document.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">{{ form.authorization_document.label }}</label>
                                    {{ form.authorization_document|add_class:"form-control" }}
                                    {% if form.authorization_document.help_text %}
                                        <div class="form-text">{{ form.authorization_document.help_text }}</div>
                                    {% endif %}
                                    {% for error in form.authorization_document.errors %}
                                        <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                        
                        <!-- Terms and Submit -->
                        <div class="form-section">
                            <div class="form-check mb-3">
                                {{ form.terms_accepted|add_class:"form-check-input" }}
                                <label class="form-check-label required-field" for="{{ form.terms_accepted.id_for_label }}">
                                    {{ form.terms_accepted.label }}
                                </label>
                                {% if form.terms_accepted.help_text %}
                                    <div class="form-text">{{ form.terms_accepted.help_text }}</div>
                                {% endif %}
                                {% for error in form.terms_accepted.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                {% endfor %}
                            </div>
                            
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary btn-lg">
                                    <i class="bi bi-send me-2"></i>Enviar Solicitação
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h6><i class="bi bi-info-circle me-2"></i>Seus Direitos pela LGPD</h6>
                </div>
                <div class="card-body">
                    <ul class="list-unstyled">
                        <li class="mb-2">
                            <i class="bi bi-check-circle text-success me-2"></i>
                            <strong>Acesso:</strong> Conhecer quais dados temos sobre você
                        </li>
                        <li class="mb-2">
                            <i class="bi bi-check-circle text-success me-2"></i>
                            <strong>Correção:</strong> Corrigir dados incorretos ou incompletos
                        </li>
                        <li class="mb-2">
                            <i class="bi bi-check-circle text-success me-2"></i>
                            <strong>Exclusão:</strong> Solicitar remoção de dados desnecessários
                        </li>
                        <li class="mb-2">
                            <i class="bi bi-check-circle text-success me-2"></i>
                            <strong>Portabilidade:</strong> Receber seus dados em formato estruturado
                        </li>
                    </ul>
                    
                    <hr>
                    
                    <p class="text-muted small">
                        <i class="bi bi-clock me-1"></i>
                        Tempo de resposta: até 15 dias conforme LGPD
                    </p>
                    
                    <p class="text-muted small">
                        <i class="bi bi-shield-check me-1"></i>
                        Seus dados estão protegidos durante todo o processo
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### 5.2 Confirmation Template

**File**: `apps/patients/templates/patients/data_request_confirmation.html`

```html
{% extends "base.html" %}
{% load static %}

{% block title %}Solicitação Enviada - LGPD{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card border-success">
                <div class="card-header bg-success text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-check-circle me-2"></i>
                        Solicitação Enviada com Sucesso
                    </h5>
                </div>
                <div class="card-body text-center py-5">
                    <i class="bi bi-envelope-check text-success" style="font-size: 4rem;"></i>
                    
                    <h4 class="mt-3 mb-4">Sua solicitação foi registrada!</h4>
                    
                    <p class="lead text-muted">
                        Você receberá um email de confirmação com o número da sua solicitação.
                    </p>
                    
                    <div class="alert alert-info mt-4">
                        <h6><i class="bi bi-info-circle me-2"></i>Próximos Passos</h6>
                        <ul class="list-unstyled mb-0 text-start">
                            <li class="mb-2">
                                <i class="bi bi-1-circle me-2"></i>
                                Nossa equipe irá verificar sua identidade
                            </li>
                            <li class="mb-2">
                                <i class="bi bi-2-circle me-2"></i>
                                Analisaremos sua solicitação conforme a LGPD
                            </li>
                            <li class="mb-2">
                                <i class="bi bi-3-circle me-2"></i>
                                Você receberá uma resposta em até 15 dias
                            </li>
                        </ul>
                    </div>
                    
                    <p class="text-muted mt-4">
                        <i class="bi bi-shield-lock me-1"></i>
                        Seus dados estão protegidos durante todo o processo conforme a LGPD
                    </p>
                    
                    <a href="{% url 'core:landing_page' %}" class="btn btn-primary mt-3">
                        <i class="bi bi-house me-2"></i>Voltar ao Início
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## Migration and Setup

### Step 6: Database Migration

```bash
# Create and run migrations
python manage.py makemigrations patients --name "add_patient_data_request_models"
python manage.py migrate

# Install required packages
pip install reportlab  # For PDF generation
```

### Step 7: Admin Configuration

**File**: `apps/patients/admin.py` (additions)

```python
from django.contrib import admin
from .models import PatientDataRequest, DataCorrectionDetail

@admin.register(PatientDataRequest)
class PatientDataRequestAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'request_type', 'requester_name', 'status', 'requested_at', 'due_date', 'is_overdue']
    list_filter = ['request_type', 'status', 'requester_relationship', 'requested_at']
    search_fields = ['request_id', 'requester_name', 'requester_email', 'patient_name_provided']
    readonly_fields = ['request_id', 'requested_at', 'due_date', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Identificação da Solicitação', {
            'fields': ['request_id', 'request_type', 'priority', 'status']
        }),
        ('Dados do Solicitante', {
            'fields': ['requester_name', 'requester_email', 'requester_phone', 'requester_relationship']
        }),
        ('Identificação do Paciente', {
            'fields': ['patient', 'patient_name_provided', 'patient_cpf_provided', 'patient_birth_date_provided', 'additional_identifiers']
        }),
        ('Solicitação', {
            'fields': ['description', 'data_export_format']
        }),
        ('Documentos', {
            'fields': ['identity_document', 'authorization_document']
        }),
        ('Processamento', {
            'fields': ['assigned_to', 'reviewed_by', 'reviewed_at', 'response_notes', 'rejection_reason', 'legal_basis_for_rejection']
        }),
        ('Resposta', {
            'fields': ['response_file', 'response_sent_at', 'anpd_notification_sent']
        }),
        ('Datas', {
            'fields': ['requested_at', 'due_date', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Em atraso'
    
    actions = ['mark_as_completed', 'export_selected']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} solicitações marcadas como concluídas.')
    mark_as_completed.short_description = 'Marcar como concluído'
```

## Testing and Validation

### Step 8: Test Data and Validation

**File**: `apps/patients/management/commands/test_patient_rights.py`

```python
from django.core.management.base import BaseCommand
from apps.patients.models import PatientDataRequest, Patient
from apps.accounts.models import EqmdCustomUser
from datetime import date

class Command(BaseCommand):
    help = 'Creates test data for patient rights system'
    
    def handle(self, *args, **options):
        # Create test patient if doesn't exist
        patient, created = Patient.objects.get_or_create(
            name="João da Silva",
            defaults={
                'birthday': date(1980, 5, 15),
                'status': 'active'
            }
        )
        
        # Create test data request
        request_data = {
            'request_type': 'access',
            'description': 'Solicito acesso a todos os meus dados médicos conforme LGPD',
            'requester_name': 'João da Silva',
            'requester_email': 'joao.silva@email.com',
            'requester_phone': '(11) 99999-9999',
            'patient_name_provided': 'João da Silva',
            'patient_birth_date_provided': date(1980, 5, 15),
            'patient': patient
        }
        
        request_obj, created = PatientDataRequest.objects.get_or_create(
            requester_email='joao.silva@email.com',
            request_type='access',
            defaults=request_data
        )
        
        if created:
            self.stdout.write(f"✓ Created test request: {request_obj.request_id}")
        else:
            self.stdout.write(f"- Test request exists: {request_obj.request_id}")
        
        # Statistics
        total_requests = PatientDataRequest.objects.count()
        pending_requests = PatientDataRequest.objects.filter(status='pending').count()
        overdue_requests = PatientDataRequest.objects.filter(
            status__in=['pending', 'under_review']
        ).count()
        
        self.stdout.write(f"\nStatistics:")
        self.stdout.write(f"- Total requests: {total_requests}")
        self.stdout.write(f"- Pending requests: {pending_requests}")
        self.stdout.write(f"- Overdue requests: {overdue_requests}")
```

## Deliverable Summary

### Files Created
1. **Models**: `PatientDataRequest`, `DataCorrectionDetail` 
2. **Forms**: `PatientDataRequestForm`, `PatientDataRequestManagementForm`
3. **Views**: Public request view, staff management views, data export
4. **Templates**: Request form, confirmation page, staff management
5. **Services**: `PatientDataExportService` for data portability
6. **Admin**: Django admin configuration for request management

### URLs Added
- `/lgpd/solicitacao/` - Public request form
- `/lgpd/solicitacao/confirmacao/` - Confirmation page  
- `/admin/lgpd/solicitacoes/` - Staff request list
- `/admin/lgpd/solicitacao/<id>/` - Request detail management
- `/admin/lgpd/export/<id>/` - Data export download

### Database Changes
- New table: `patients_patientdatarequest`
- New table: `patients_datacorrectiondetail`
- Indexes for performance on common queries
- File upload fields for documents

## Next Phase

After completing Phase 2, proceed to **Phase 3: Privacy Transparency** to implement privacy policies, data processing notices, and consent management systems.

---

**Phase 2 Completion Criteria**:
- [ ] All models created and migrated
- [ ] Public request form functional and accessible
- [ ] Email notifications working
- [ ] Staff admin interface operational
- [ ] Data export functionality tested
- [ ] Forms validate input correctly
- [ ] Request workflow from submission to completion functional