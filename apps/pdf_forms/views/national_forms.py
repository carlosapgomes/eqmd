from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import FormView
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django import forms

from apps.core.permissions.utils import can_access_patient
from ..models import PDFFormTemplate, PDFFormSubmission
from ..permissions import check_pdf_form_access, check_pdf_form_creation
from ..security import PDFFormSecurity
from ..services.field_mapping import DataFieldMapper
from apps.core.models import MedicalProcedure


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
        required=True,
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

        return cleaned_data
        
    def _clean_icd_field(self, field_name, required=False):
        icd_value = (self.cleaned_data.get(field_name) or '').upper().strip()
        if not icd_value:
            if required:
                raise forms.ValidationError("CID 10 é obrigatório")
            return ''

        # TODO: Replace with search/select-only validation once ICD lookup is implemented.
        return icd_value

    def clean_main_icd(self):
        return self._clean_icd_field('main_icd', required=True)

    def clean_secondary_icd(self):
        return self._clean_icd_field('secondary_icd', required=False)

    def clean_other_icd(self):
        return self._clean_icd_field('other_icd', required=False)
    

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
        
        # Pre-fill patient data
        form.fields['patient_name'].initial = self.patient.name
        form.fields['patient_gender'].initial = self.patient.get_gender_display()
        if self.patient.birthday:
            form.fields['patient_birth_date'].initial = self.patient.birthday
        if 'medical_record_number' in form.fields and hasattr(self.patient, 'current_record_number'):
            form.fields['medical_record_number'].initial = self.patient.current_record_number

        user = self.request.user
        form.fields['doctor_name'].initial = user.get_full_name() or user.username
        if user.fiscal_number:
            form.fields['doctor_doc_number_fiscal_number'].initial = user.fiscal_number
        form.fields['request_date'].initial = timezone.localdate().isoformat()
            
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

            procedure_ids = {
                slot['id']: form.cleaned_data.get(slot['id'])
                for slot in APACForm.PROCEDURE_SLOTS
            }
            selected_ids = [proc_id for proc_id in procedure_ids.values() if proc_id]
            procedures = MedicalProcedure.objects.in_bulk(selected_ids)

            # Prepare form data for storage
            form_data = {
                'patient_name': form.cleaned_data['patient_name'],
                'patient_gender': form.cleaned_data['patient_gender'],
                'patient_birth_date': form.cleaned_data['patient_birth_date'].isoformat() if form.cleaned_data.get('patient_birth_date') else '',
                'patient_record_number': (
                    form.cleaned_data.get('medical_record_number')
                    or getattr(self.patient, 'current_record_number', '')
                    or ''
                ),
                'patient_address': getattr(self.patient, 'address', '') or '',
                'patient_city': getattr(self.patient, 'city', '') or '',
                'patient_state': getattr(self.patient, 'state', '') or '',
                'patient_zip_code': getattr(self.patient, 'zip_code', '') or '',
                'patient_sus_card': getattr(self.patient, 'healthcard_number', '') or '',
                'patient_phone': getattr(self.patient, 'phone', '') or '',
                'hospital_name': getattr(settings, 'HOSPITAL_CONFIG', {}).get('name', ''),
                'hospital_cnes': getattr(settings, 'HOSPITAL_CONFIG', {}).get('cnes', ''),
                'main_diagnosis': form.cleaned_data['main_diagnosis'],
                'main_icd': form.cleaned_data['main_icd'],
                'secondary_icd': form.cleaned_data.get('secondary_icd', ''),
                'other_icd': form.cleaned_data.get('other_icd', ''),
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
            }
            if self.patient and self.patient.gender:
                gender_auto_fill = DataFieldMapper.process_gender_auto_fill(
                    apac_template.form_fields or {}, self.patient.gender
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

            # Create submission
            submission = PDFFormSubmission(
                form_template=apac_template,
                patient=self.patient,
                created_by=self.request.user,
                updated_by=self.request.user,
                event_datetime=timezone.now(),
                description=f"APAC: {main_procedure.code if main_procedure else ''}",
                form_data=form_data,
            )
            submission.save()
            
            messages.success(
                self.request,
                f"Formulário APAC criado com sucesso! Procedimento: {main_procedure.code if main_procedure else ''}"
            )
            return redirect('pdf_forms:submission_detail', pk=submission.pk)
            
        except Exception as e:
            messages.error(
                self.request,
                f"Erro ao processar formulário APAC: {str(e)}"
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(
            self.request,
            "Por favor, corrija os erros no formulário."
        )
        return super().form_invalid(form)


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
