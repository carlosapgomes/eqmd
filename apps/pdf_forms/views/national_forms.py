from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import FormView
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django import forms

from apps.core.permissions.utils import can_access_patient
from ..models import PDFFormTemplate, PDFFormSubmission
from ..permissions import check_pdf_form_access, check_pdf_form_creation
from ..security import PDFFormSecurity
from apps.core.models import MedicalProcedure


class APACForm(forms.Form):
    """Hardcoded APAC form with complex validation."""
    
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
        widget=forms.DateInput(attrs={'readonly': True, 'class': 'form-control', 'type': 'date'})
    )
    
    patient_cns = forms.CharField(
        label="CNS",
        required=False,
        widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    
    # Procedure selection with search
    procedure = forms.ModelChoiceField(
        label="Procedimento",
        queryset=MedicalProcedure.objects.filter(is_active=True),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite para buscar procedimento...',
            'autocomplete': 'off'
        }),
        required=True,
        error_messages={'required': 'Selecione um procedimento'}
    )
    
    # APAC specific fields
    apac_type = forms.ChoiceField(
        label="Tipo de APAC",
        choices=[
            ('1', 'APAC de Continuidade'),
            ('2', 'APAC de Inicialização'),
            ('3', 'APAC de Renovação'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    authorization_date = forms.DateField(
        label="Data de Autorização",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    
    cid_code = forms.CharField(
        label="Código CID-10",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A00.0'}),
        required=True,
        help_text="Código da Classificação Internacional de Doenças"
    )
    
    main_diagnosis = forms.CharField(
        label="Diagnóstico Principal",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=True
    )
    
    additional_info = forms.CharField(
        label="Informações Adicionais",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    
    def clean_procedure(self):
        """Validate procedure selection."""
        procedure = self.cleaned_data.get('procedure')
        if not procedure:
            raise forms.ValidationError("Selecione um procedimento válido")
        return procedure
        
    def clean_cid_code(self):
        """Validate CID code format."""
        cid_code = self.cleaned_data.get('cid_code', '').upper().strip()
        if not cid_code:
            raise forms.ValidationError("Código CID é obrigatório")
        
        # Basic CID-10 format validation (letter + digits + optional decimal)
        import re
        if not re.match(r'^[A-Z]\d{2}(\.\d{1,2})?$', cid_code):
            raise forms.ValidationError("Formato de CID-10 inválido. Use formato como A00.0")
        
        return cid_code
    
    def clean_authorization_date(self):
        """Validate authorization date is not in the future."""
        date = self.cleaned_data.get('authorization_date')
        if date and date > timezone.now().date():
            raise forms.ValidationError("Data de autorização não pode ser futura")
        return date


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
        if self.patient.birth_date:
            form.fields['patient_birth_date'].initial = self.patient.birth_date
        if hasattr(self.patient, 'cns'):
            form.fields['patient_cns'].initial = self.patient.cns
            
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
            
            # Prepare form data for storage
            form_data = {
                'patient_name': form.cleaned_data['patient_name'],
                'patient_gender': form.cleaned_data['patient_gender'],
                'patient_birth_date': form.cleaned_data['patient_birth_date'].isoformat() if form.cleaned_data.get('patient_birth_date') else '',
                'patient_cns': form.cleaned_data.get('patient_cns', ''),
                'procedure_code': form.cleaned_data['procedure'].code,
                'procedure_description': form.cleaned_data['procedure'].description,
                'apac_type': form.cleaned_data['apac_type'],
                'apac_type_display': dict(APACForm.fields['apac_type'].choices).get(form.cleaned_data['apac_type']),
                'authorization_date': form.cleaned_data['authorization_date'].isoformat(),
                'cid_code': form.cleaned_data['cid_code'],
                'main_diagnosis': form.cleaned_data['main_diagnosis'],
                'additional_info': form.cleaned_data.get('additional_info', ''),
            }
            
            # Create submission
            submission = PDFFormSubmission(
                form_template=apac_template,
                patient=self.patient,
                created_by=self.request.user,
                updated_by=self.request.user,
                event_datetime=timezone.now(),
                description=f"APAC: {form.cleaned_data['procedure'].code}",
                form_data=form_data,
            )
            submission.save()
            
            messages.success(
                self.request,
                f"Formulário APAC criado com sucesso! Procedimento: {form.cleaned_data['procedure'].code}"
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