from django import forms
from .models import PatientDataRequest, DataCorrectionDetail
from apps.patients.models import Patient
from django.core.exceptions import ValidationError
import re


class PatientDataRequestCreationForm(forms.ModelForm):
    """Staff form to create patient data requests during in-person visits"""

    # Patient selection field
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Selecione o paciente se já cadastrado no sistema"
    )

    class Meta:
        model = PatientDataRequest
        fields = [
            'patient', 'request_type', 'description', 'priority',
            'requester_name', 'requester_email', 'requester_phone', 
            'requester_relationship', 'patient_name_provided',
            'patient_cpf_provided', 'patient_birth_date_provided', 
            'additional_identifiers', 'data_export_format'
        ]

        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Descreva detalhadamente a solicitação do paciente/responsável...',
                'class': 'form-control'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
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
            'patient': 'Paciente (se cadastrado)',
            'request_type': 'Tipo de Solicitação LGPD',
            'description': 'Descrição da Solicitação',
            'priority': 'Prioridade',
            'requester_name': 'Nome do Solicitante',
            'requester_email': 'Email do Solicitante',
            'requester_phone': 'Telefone (opcional)',
            'requester_relationship': 'Relação com o Paciente',
            'patient_name_provided': 'Nome do Paciente',
            'patient_cpf_provided': 'CPF do Paciente (opcional)',
            'patient_birth_date_provided': 'Data de Nascimento do Paciente',
            'additional_identifiers': 'Informações Adicionais para Identificação',
            'data_export_format': 'Formato de Exportação',
        }

        help_texts = {
            'request_type': 'Direito exercido conforme LGPD Art. 18',
            'description': 'Detalhes específicos da solicitação feita presencialmente',
            'priority': 'Prioridade baseada na urgência e complexidade',
            'patient_cpf_provided': 'Opcional, mas ajuda na identificação',
            'additional_identifiers': 'Informações que ajudem a identificar o paciente',
            'requester_relationship': 'Verificar documentação de representação legal se necessário',
        }

    def clean(self):
        cleaned_data = super().clean()

        # Validate CPF format if provided
        cpf = cleaned_data.get('patient_cpf_provided')
        if cpf:
            cpf_clean = re.sub(r'[^\d]', '', cpf)
            if len(cpf_clean) != 11:
                raise ValidationError({'patient_cpf_provided': 'CPF deve ter 11 dígitos'})

        # If patient is selected, auto-fill patient data
        patient = cleaned_data.get('patient')
        if patient:
            cleaned_data['patient_name_provided'] = patient.name
            if hasattr(patient, 'birthday') and patient.birthday:
                cleaned_data['patient_birth_date_provided'] = patient.birthday

        return cleaned_data


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


class DataCorrectionDetailForm(forms.ModelForm):
    """Form for managing data correction details"""

    class Meta:
        model = DataCorrectionDetail
        fields = [
            'field_name', 'current_value', 'requested_value', 'justification',
            'approved', 'review_notes'
        ]

        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'form-control'}),
            'current_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'requested_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'justification': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'approved': forms.Select(choices=[(None, '---'), (True, 'Aprovado'), (False, 'Rejeitado')], attrs={'class': 'form-select'}),
            'review_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }