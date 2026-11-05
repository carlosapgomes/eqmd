import logging
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import FormView
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django import forms

from apps.core.permissions.utils import (
    can_access_patient,
    can_edit_event,
    is_doctor_or_resident,
)
from ..models import PDFFormTemplate, PDFFormSubmission
from ..permissions import check_pdf_form_access, check_pdf_form_creation
from ..security import PDFFormSecurity
from ..services.field_mapping import DataFieldMapper
from .base_views import visible_pdf_submissions
from apps.core.models import MedicalProcedure

logger = logging.getLogger(__name__)

DRAFT_APPROVAL_DENIED_MESSAGE = (
    "Apenas médicos e residentes podem aprovar rascunhos de formulários APAC."
)


def build_apac_form_data(form, patient, template):
    """Build the stored APAC form data from a validated APAC form.

    Shared by the create and update flows so both capture the same clinical
    fields and overlay mapping (design D8).
    """
    procedure_ids = {
        slot['id']: form.cleaned_data.get(slot['id'])
        for slot in APACForm.PROCEDURE_SLOTS
    }
    selected_ids = [proc_id for proc_id in procedure_ids.values() if proc_id]
    procedures = MedicalProcedure.objects.in_bulk(selected_ids)

    # Get ICD-10 codes
    icd10_ids = {
        'main_icd_id': form.cleaned_data.get('main_icd_id'),
        'secondary_icd_id': form.cleaned_data.get('secondary_icd_id'),
        'other_icd_id': form.cleaned_data.get('other_icd_id'),
    }
    selected_icd_ids = [icd_id for icd_id in icd10_ids.values() if icd_id]
    from apps.core.models import Icd10Code
    icd10_codes = Icd10Code.objects.in_bulk(selected_icd_ids)

    # Prepare form data for storage
    def resolve_icd_code(fallback_key, display_key, icd_id):
        value = (form.cleaned_data.get(fallback_key) or '').strip()
        if value:
            return value
        display_value = (form.cleaned_data.get(display_key) or '').strip()
        if display_value:
            return display_value
        icd_obj = icd10_codes.get(icd_id)
        return icd_obj.code if icd_obj else ''

    form_data = {
        'patient_name': form.cleaned_data['patient_name'],
        'patient_gender': form.cleaned_data['patient_gender'],
        'patient_birth_date': form.cleaned_data['patient_birth_date'].isoformat() if form.cleaned_data.get('patient_birth_date') else '',
        'patient_record_number': (
            form.cleaned_data.get('medical_record_number')
            or getattr(patient, 'current_record_number', '')
            or ''
        ),
        'patient_address': getattr(patient, 'address', '') or '',
        'patient_city': getattr(patient, 'city', '') or '',
        'patient_state': getattr(patient, 'state', '') or '',
        'patient_zip_code': getattr(patient, 'zip_code', '') or '',
        'patient_sus_card': getattr(patient, 'healthcard_number', '') or '',
        'patient_phone': getattr(patient, 'phone', '') or '',
        'hospital_name': getattr(settings, 'HOSPITAL_CONFIG', {}).get('name', ''),
        'hospital_cnes': getattr(settings, 'HOSPITAL_CONFIG', {}).get('cnes', ''),
        'main_diagnosis': form.cleaned_data['main_diagnosis'],
        'main_icd': resolve_icd_code('main_icd', 'main_icd_display', icd10_ids.get('main_icd_id')),
        'secondary_icd': resolve_icd_code('secondary_icd', 'secondary_icd_display', icd10_ids.get('secondary_icd_id')),
        'other_icd': resolve_icd_code('other_icd', 'other_icd_display', icd10_ids.get('other_icd_id')),
        'diagnosis_notes': form.cleaned_data.get('diagnosis_notes', ''),
        'doctor_name': form.cleaned_data.get('doctor_name', ''),
        'request_date': form.cleaned_data['request_date'].isoformat() if form.cleaned_data.get('request_date') else '',
        'doctor_doc_type_fiscal_number': bool(form.cleaned_data.get('doctor_doc_type_fiscal_number')),
        'doctor_doc_number_fiscal_number': form.cleaned_data.get('doctor_doc_number_fiscal_number', ''),
        'main_procedure_quantity': form.cleaned_data.get('main_procedure_quantity', '') or '',
        'secondary_procedure_1_qty': form.cleaned_data.get('secondary_procedure_1_qty', '') or '',
        'secondary_procedure_2_qty': form.cleaned_data.get('secondary_procedure_2_qty', '') or '',
        'secondary_procedure_3_qty': form.cleaned_data.get('secondary_procedure_3_qty', '') or '',
        'secondary_procedure_4_qty': form.cleaned_data.get('secondary_procedure_4_qty', '') or '',
        'secondary_procedure_5_qty': form.cleaned_data.get('secondary_procedure_5_qty', '') or '',
        # ICD-10 codes
        'main_icd_id': str(icd10_ids.get('main_icd_id')) if icd10_ids.get('main_icd_id') else '',
        'main_icd_code': icd10_codes.get(icd10_ids.get('main_icd_id')).code if icd10_codes.get(icd10_ids.get('main_icd_id')) else '',
        'main_icd_description': icd10_codes.get(icd10_ids.get('main_icd_id')).description if icd10_codes.get(icd10_ids.get('main_icd_id')) else '',
        'secondary_icd_id': str(icd10_ids.get('secondary_icd_id')) if icd10_ids.get('secondary_icd_id') else '',
        'secondary_icd_code': icd10_codes.get(icd10_ids.get('secondary_icd_id')).code if icd10_codes.get(icd10_ids.get('secondary_icd_id')) else '',
        'secondary_icd_description': icd10_codes.get(icd10_ids.get('secondary_icd_id')).description if icd10_codes.get(icd10_ids.get('secondary_icd_id')) else '',
        'other_icd_id': str(icd10_ids.get('other_icd_id')) if icd10_ids.get('other_icd_id') else '',
        'other_icd_code': icd10_codes.get(icd10_ids.get('other_icd_id')).code if icd10_codes.get(icd10_ids.get('other_icd_id')) else '',
        'other_icd_description': icd10_codes.get(icd10_ids.get('other_icd_id')).description if icd10_codes.get(icd10_ids.get('other_icd_id')) else '',
    }
    if patient and patient.gender:
        gender_auto_fill = DataFieldMapper.process_gender_auto_fill(
            template.form_fields or {}, patient.gender
        )
        form_data.update(gender_auto_fill)

    for slot in APACForm.PROCEDURE_SLOTS:
        slot_id = slot['id']
        procedure_id = procedure_ids.get(slot_id)
        procedure = procedures.get(procedure_id) if procedure_id else None

        form_data[f"{slot_id}_id"] = str(procedure.id) if procedure else ''
        form_data[f"{slot_id}_code"] = procedure.code if procedure else ''
        form_data[f"{slot_id}_description"] = procedure.description if procedure else ''

    main_procedure = procedures.get(procedure_ids.get('main_procedure'))

    # Backward compatibility for existing overlays
    if main_procedure:
        form_data['procedure_code'] = main_procedure.code
        form_data['procedure_description'] = main_procedure.description

    return form_data


class APACForm(forms.Form):
    """Hardcoded APAC form with complex validation."""

    PROCEDURE_SLOTS = [
        {
            'id': 'main_procedure',
            'display': 'main_procedure_display',
            'label': 'Procedimento Principal',
            'placeholder': 'Digite para buscar procedimento principal...',
            'results_id': 'procedure-results-main',
            'required': True,
        },
        {
            'id': 'secondary_procedure_1',
            'display': 'secondary_procedure_1_display',
            'label': 'Procedimento Secundário 1',
            'placeholder': 'Digite para buscar procedimento secundário 1...',
            'results_id': 'procedure-results-secondary-1',
            'required': False,
        },
        {
            'id': 'secondary_procedure_2',
            'display': 'secondary_procedure_2_display',
            'label': 'Procedimento Secundário 2',
            'placeholder': 'Digite para buscar procedimento secundário 2...',
            'results_id': 'procedure-results-secondary-2',
            'required': False,
        },
        {
            'id': 'secondary_procedure_3',
            'display': 'secondary_procedure_3_display',
            'label': 'Procedimento Secundário 3',
            'placeholder': 'Digite para buscar procedimento secundário 3...',
            'results_id': 'procedure-results-secondary-3',
            'required': False,
        },
        {
            'id': 'secondary_procedure_4',
            'display': 'secondary_procedure_4_display',
            'label': 'Procedimento Secundário 4',
            'placeholder': 'Digite para buscar procedimento secundário 4...',
            'results_id': 'procedure-results-secondary-4',
            'required': False,
        },
        {
            'id': 'secondary_procedure_5',
            'display': 'secondary_procedure_5_display',
            'label': 'Procedimento Secundário 5',
            'placeholder': 'Digite para buscar procedimento secundário 5...',
            'results_id': 'procedure-results-secondary-5',
            'required': False,
        },
    ]
    
    # Patient fields (auto-filled)
    patient_name = forms.CharField(
        label="Nome do Paciente",
        widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    
    patient_gender = forms.CharField(
        label="Sexo",
        widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    
    patient_birth_date = forms.DateField(
        label="Data de Nascimento",
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'readonly': True, 'class': 'form-control', 'type': 'date'}
        )
    )
    
    main_procedure_quantity = forms.CharField(
        label="Quantidade",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    secondary_procedure_1_qty = forms.CharField(
        label="Quantidade",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    secondary_procedure_2_qty = forms.CharField(
        label="Quantidade",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    secondary_procedure_3_qty = forms.CharField(
        label="Quantidade",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    secondary_procedure_4_qty = forms.CharField(
        label="Quantidade",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    secondary_procedure_5_qty = forms.CharField(
        label="Quantidade",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Procedure selection with search (main + secondary)
    main_procedure = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'procedure-hidden-input'})
    )
    main_procedure_display = forms.CharField(
        label="Procedimento Principal",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control procedure-search-input',
            'placeholder': 'Digite para buscar procedimento principal...',
            'autocomplete': 'off',
            'data-results-id': 'procedure-results-main',
            'data-hidden-id': 'id_main_procedure',
            'data-required': 'true',
        })
    )

    secondary_procedure_1 = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'procedure-hidden-input'})
    )
    secondary_procedure_1_display = forms.CharField(
        label="Procedimento Secundário 1",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control procedure-search-input',
            'placeholder': 'Digite para buscar procedimento secundário 1...',
            'autocomplete': 'off',
            'data-results-id': 'procedure-results-secondary-1',
            'data-hidden-id': 'id_secondary_procedure_1',
        })
    )

    secondary_procedure_2 = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'procedure-hidden-input'})
    )
    secondary_procedure_2_display = forms.CharField(
        label="Procedimento Secundário 2",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control procedure-search-input',
            'placeholder': 'Digite para buscar procedimento secundário 2...',
            'autocomplete': 'off',
            'data-results-id': 'procedure-results-secondary-2',
            'data-hidden-id': 'id_secondary_procedure_2',
        })
    )

    secondary_procedure_3 = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'procedure-hidden-input'})
    )
    secondary_procedure_3_display = forms.CharField(
        label="Procedimento Secundário 3",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control procedure-search-input',
            'placeholder': 'Digite para buscar procedimento secundário 3...',
            'autocomplete': 'off',
            'data-results-id': 'procedure-results-secondary-3',
            'data-hidden-id': 'id_secondary_procedure_3',
        })
    )

    secondary_procedure_4 = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'procedure-hidden-input'})
    )
    secondary_procedure_4_display = forms.CharField(
        label="Procedimento Secundário 4",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control procedure-search-input',
            'placeholder': 'Digite para buscar procedimento secundário 4...',
            'autocomplete': 'off',
            'data-results-id': 'procedure-results-secondary-4',
            'data-hidden-id': 'id_secondary_procedure_4',
        })
    )

    secondary_procedure_5 = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'procedure-hidden-input'})
    )
    secondary_procedure_5_display = forms.CharField(
        label="Procedimento Secundário 5",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control procedure-search-input',
            'placeholder': 'Digite para buscar procedimento secundário 5...',
            'autocomplete': 'off',
            'data-results-id': 'procedure-results-secondary-5',
            'data-hidden-id': 'id_secondary_procedure_5',
        })
    )
    
    main_diagnosis = forms.CharField(
        label="Diagnóstico Principal",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=True
    )

    main_icd = forms.CharField(
        label="CID 10 Principal",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A00.0'}),
        required=False,
        help_text="Código da Classificação Internacional de Doenças"
    )

    secondary_icd = forms.CharField(
        label="CID 10 Secundário",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A00.0'}),
        required=False
    )

    other_icd = forms.CharField(
        label="CID 10 Causas Associadas",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A00.0'}),
        required=False
    )

    # ICD-10 code selection with search (main + secondary)
    main_icd_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'icd10-hidden-input'})
    )
    main_icd_display = forms.CharField(
        label="CID 10 Principal",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control icd10-search-input',
            'placeholder': 'Digite para buscar CID 10 principal...',
            'autocomplete': 'off',
            'data-results-id': 'icd10-results-main',
            'data-hidden-id': 'id_main_icd_id',
            'data-required': 'true',
        })
    )

    secondary_icd_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'icd10-hidden-input'})
    )
    secondary_icd_display = forms.CharField(
        label="CID 10 Secundário",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control icd10-search-input',
            'placeholder': 'Digite para buscar CID 10 secundário...',
            'autocomplete': 'off',
            'data-results-id': 'icd10-results-secondary',
            'data-hidden-id': 'id_secondary_icd_id',
        })
    )

    other_icd_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'icd10-hidden-input'})
    )
    other_icd_display = forms.CharField(
        label="CID 10 Causas Associadas",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control icd10-search-input',
            'placeholder': 'Digite para buscar CID 10 causas associadas...',
            'autocomplete': 'off',
            'data-results-id': 'icd10-results-other',
            'data-hidden-id': 'id_other_icd_id',
        })
    )

    diagnosis_notes = forms.CharField(
        label="Observações",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )

    doctor_name = forms.CharField(
        label="Nome do Profissional",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    request_date = forms.DateField(
        label="Data da Solicitação",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    doctor_doc_type_fiscal_number = forms.BooleanField(
        label="CPF",
        required=False,
        initial=True
    )

    doctor_doc_number_fiscal_number = forms.CharField(
        label="Número do CPF",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    def _procedure_slots(self):
        return [
            (slot['id'], slot['display'], slot['required'])
            for slot in self.PROCEDURE_SLOTS
        ]

    def _icd10_slots(self):
        """Return ICD-10 field definitions for validation."""
        return [
            ('main_icd_id', 'main_icd_display', True),
            ('secondary_icd_id', 'secondary_icd_display', False),
            ('other_icd_id', 'other_icd_display', False),
        ]

    def clean(self):
        cleaned_data = super().clean()

        selected_ids = {}
        for id_field, display_field, required in self._procedure_slots():
            display_value = (cleaned_data.get(display_field) or '').strip()
            procedure_id = cleaned_data.get(id_field)

            if required and not procedure_id:
                self.add_error(display_field, "Selecione um procedimento válido da lista de sugestões.")
                continue

            if display_value and not procedure_id:
                self.add_error(display_field, "Selecione um procedimento válido da lista de sugestões.")
                continue

            if procedure_id:
                procedure_id_str = str(procedure_id)
                selected_ids.setdefault(procedure_id_str, []).append(display_field)

        for display_fields in selected_ids.values():
            if len(display_fields) > 1:
                for field in display_fields:
                    self.add_error(field, "Procedimento duplicado. Escolha outro.")

        if selected_ids:
            valid_ids = set(
                str(proc_id) for proc_id in MedicalProcedure.objects.filter(
                    id__in=list(selected_ids.keys()),
                    is_active=True
                ).values_list('id', flat=True)
            )
            for proc_id, display_fields in selected_ids.items():
                if proc_id not in valid_ids:
                    for field in display_fields:
                        self.add_error(field, "Procedimento inválido ou inativo.")

        # Validate ICD-10 codes
        selected_icd_ids = {}
        for id_field, display_field, required in self._icd10_slots():
            display_value = (cleaned_data.get(display_field) or '').strip()
            icd_id = cleaned_data.get(id_field)

            if required and not icd_id:
                self.add_error(display_field, "Selecione um CID 10 válido da lista de sugestões.")
                continue

            if display_value and not icd_id:
                self.add_error(display_field, "Selecione um CID 10 válido da lista de sugestões.")
                continue

            if icd_id:
                icd_id_str = str(icd_id)
                selected_icd_ids.setdefault(icd_id_str, []).append(display_field)

        if selected_icd_ids:
            from apps.core.models import Icd10Code
            valid_icd_ids = set(
                str(code_id) for code_id in Icd10Code.objects.filter(
                    id__in=list(selected_icd_ids.keys()),
                    is_active=True
                ).values_list('id', flat=True)
            )
            for icd_id, display_fields in selected_icd_ids.items():
                if icd_id not in valid_icd_ids:
                    for field in display_fields:
                        self.add_error(field, "CID 10 inválido ou inativo.")

        return cleaned_data
    

def _stored_date(value):
    """Return the stored ISO date string as a date, or None."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def apply_apac_patient_defaults(form, patient, user):
    """Pre-fill the APAC identification fields for the submitting user."""
    form.fields['patient_name'].initial = patient.name
    form.fields['patient_gender'].initial = patient.get_gender_display()
    if patient.birthday:
        form.fields['patient_birth_date'].initial = patient.birthday
    if 'medical_record_number' in form.fields and hasattr(patient, 'current_record_number'):
        form.fields['medical_record_number'].initial = patient.current_record_number
    form.fields['doctor_name'].initial = user.get_full_name() or user.username
    if user.fiscal_number:
        form.fields['doctor_doc_number_fiscal_number'].initial = user.fiscal_number
    form.fields['request_date'].initial = timezone.localdate().isoformat()


def build_apac_initial_data(form_data):
    """Map a stored APAC submission back onto the hardcoded APAC form fields.

    Used by the update view so the persisted submission prefills the same
    capture machinery that produced it (design D8). Unknown keys are ignored;
    a procedure or ICD-10 entry is only restored when its stored UUID exists.
    """
    initial = {
        'patient_name': form_data.get('patient_name', ''),
        'patient_gender': form_data.get('patient_gender', ''),
        'patient_birth_date': _stored_date(form_data.get('patient_birth_date')),
        'main_diagnosis': form_data.get('main_diagnosis', ''),
        'main_icd': form_data.get('main_icd', ''),
        'secondary_icd': form_data.get('secondary_icd', ''),
        'other_icd': form_data.get('other_icd', ''),
        'diagnosis_notes': form_data.get('diagnosis_notes', ''),
        'doctor_name': form_data.get('doctor_name', ''),
        'request_date': _stored_date(form_data.get('request_date')),
        'doctor_doc_type_fiscal_number': bool(
            form_data.get('doctor_doc_type_fiscal_number')
        ),
        'doctor_doc_number_fiscal_number': form_data.get(
            'doctor_doc_number_fiscal_number', ''
        ),
    }

    for slot in APACForm.PROCEDURE_SLOTS:
        slot_id = slot['id']
        initial[slot_id] = form_data.get(f'{slot_id}_id') or None
        code = form_data.get(f'{slot_id}_code') or ''
        description = form_data.get(f'{slot_id}_description') or ''
        initial[slot['display']] = (
            f'{code} - {description}' if code or description else ''
        )
        qty_field = (
            'main_procedure_quantity'
            if slot_id == 'main_procedure'
            else f'{slot_id}_qty'
        )
        initial[qty_field] = form_data.get(qty_field, '')

    for id_field, code_field, display_field in (
        ('main_icd_id', 'main_icd_code', 'main_icd_display'),
        ('secondary_icd_id', 'secondary_icd_code', 'secondary_icd_display'),
        ('other_icd_id', 'other_icd_code', 'other_icd_display'),
    ):
        initial[id_field] = form_data.get(id_field) or None
        initial[display_field] = form_data.get(code_field, '')

    return initial


class APACFormView(LoginRequiredMixin, FormView):
    """Hardcoded APAC form view with complex business logic."""
    
    template_name = 'pdf_forms/apac_form.html'
    form_class = APACForm
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions and setup patient."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        # Get patient
        from apps.patients.models import Patient
        self.patient = get_object_or_404(Patient, id=kwargs['patient_id'])
        
        # Check permissions
        check_pdf_form_creation(request.user, self.patient)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form(self, form_class=None):
        """Get form with patient pre-filled data."""
        if form_class is None:
            form_class = self.get_form_class()
        
        form = super().get_form(form_class)
        apply_apac_patient_defaults(form, self.patient, self.request.user)
            
        return form
    
    def get_context_data(self, **kwargs):
        """Add patient and procedure search context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['form_type'] = 'APAC'
        return context
    
    def form_valid(self, form):
        """Process APAC form submission."""
        try:
            # Get or create APAC template
            apac_template, created = PDFFormTemplate.objects.get_or_create(
                form_type='APAC',
                defaults={
                    'name': 'APAC - Formulário Nacional',
                    'description': 'Formulário de APAC (Autorização de Procedimentos de Alta Complexidade)',
                    'form_type': 'APAC',
                    'hospital_specific': False,
                    'is_active': True,
                    'created_by': self.request.user,
                    'form_fields': {}  # Empty fields for hardcoded forms
                }
            )

            form_data = build_apac_form_data(form, self.patient, apac_template)
            main_procedure_code = form_data.get('main_procedure_code', '')

            # Create submission
            submission = PDFFormSubmission(
                form_template=apac_template,
                patient=self.patient,
                created_by=self.request.user,
                updated_by=self.request.user,
                event_datetime=timezone.now(),
                description=f"APAC: {main_procedure_code}",
                form_data=form_data,
            )
            submission.save()
            
            messages.success(
                self.request,
                f"Formulário APAC criado com sucesso! Procedimento: {main_procedure_code}"
            )
            return redirect('pdf_forms:submission_detail', pk=submission.pk)
            
        except Exception as e:
            logger.exception(
                "APAC form submission failed (user_id=%s, patient_id=%s)",
                getattr(self.request.user, "id", None),
                getattr(self.patient, "id", None),
            )
            messages.error(
                self.request,
                f"Erro ao processar formulário APAC: {str(e)}"
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        error_fields = list(form.errors.keys())
        logger.warning(
            "APAC form validation failed (user_id=%s, patient_id=%s, fields=%s)",
            getattr(self.request.user, "id", None),
            getattr(self.patient, "id", None),
            error_fields,
        )
        messages.error(
            self.request,
            "Por favor, corrija os erros no formulário."
        )
        return super().form_invalid(form)


class APACFormUpdateView(LoginRequiredMixin, FormView):
    """Edit a persisted APAC submission in place.

    APAC capture joins the standard event semantics (design D8): the
    hardcoded form is prefilled from the stored submission, saving updates the
    same row, and the draft/finalize actions follow the supervision rules.
    """

    template_name = 'pdf_forms/apac_form.html'
    form_class = APACForm

    def dispatch(self, request, *args, **kwargs):
        """Resolve the submission and check access and edit rights."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        self.submission = get_object_or_404(
            visible_pdf_submissions(), pk=kwargs['pk']
        )

        # Only APAC submissions belong to this capture flow.
        if self.submission.form_template.form_type != 'APAC':
            raise Http404("APAC submission not found")

        check_pdf_form_access(request.user, self.submission.patient)

        if not can_edit_event(request.user, self.submission):
            raise PermissionDenied(
                "You don't have permission to edit this APAC submission"
            )

        self.patient = self.submission.patient
        self.form_template = self.submission.form_template

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        """Prefill the hardcoded APAC form from the stored submission."""
        if form_class is None:
            form_class = self.get_form_class()

        form = super().get_form(form_class)
        apply_apac_patient_defaults(form, self.patient, self.request.user)
        form.initial.update(build_apac_initial_data(self.submission.form_data))

        return form

    def get_context_data(self, **kwargs):
        """Add patient, submission and supervision context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        context['form_type'] = 'APAC'
        context['submission'] = self.submission
        context['is_update'] = True
        context['is_draft_submission'] = self.submission.is_draft
        context['can_finalize'] = (
            self.submission.is_draft
            and is_doctor_or_resident(self.request.user)
        )
        return context

    def _submitted_action(self):
        """Return the supervision action submitted by the form buttons."""
        if 'save_final' in self.request.POST:
            return 'save_final'
        if 'save_draft' in self.request.POST:
            return 'save_draft'
        return None

    def post(self, request, *args, **kwargs):
        """Reject a crafted student approval before the error guard."""
        if (
            self.submission.is_draft
            and self._submitted_action() == 'save_final'
            and not is_doctor_or_resident(request.user)
        ):
            raise PermissionDenied(DRAFT_APPROVAL_DENIED_MESSAGE)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """Persist the corrected submission, keeping or promoting its state."""
        action = self._submitted_action()
        was_draft = self.submission.is_draft

        try:
            form_data = build_apac_form_data(form, self.patient, self.form_template)

            submission = self.submission
            submission.form_data = form_data
            submission.updated_by = self.request.user

            if was_draft and action == 'save_final':
                submission.is_draft = False
                submission.draft_promoted_at = timezone.now()
                submission.draft_promoted_by = self.request.user
            elif was_draft:
                submission.is_draft = True

            submission.save()

            messages.success(
                self.request,
                f"Formulário APAC de {self.patient.name} atualizado com sucesso!"
            )
            return redirect('pdf_forms:submission_detail', pk=submission.pk)

        except Exception as e:
            logger.exception(
                "APAC submission update failed (user_id=%s, submission_id=%s)",
                getattr(self.request.user, "id", None),
                getattr(self.submission, "id", None),
            )
            messages.error(
                self.request,
                f"Erro ao processar formulário APAC: {e!s}"
            )
            return self.form_invalid(form)


class AIHFormView(LoginRequiredMixin, FormView):
    """Placeholder for future AIH form implementation."""
    
    template_name = 'pdf_forms/aih_form.html'
    
    def get(self, request, *args, **kwargs):
        """Show placeholder message."""
        from apps.patients.models import Patient
        patient = get_object_or_404(Patient, id=kwargs['patient_id'])
        
        messages.info(
            request,
            "Formulário AIH em desenvolvimento. Funcionalidade disponível em breve."
        )
        
        return redirect('pdf_forms:form_select', patient_id=patient.id)
