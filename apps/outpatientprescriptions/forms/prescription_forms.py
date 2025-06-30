from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from django.db import models
from apps.events.forms import EventForm
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.drugtemplates.models import DrugTemplate
from apps.outpatientprescriptions.widgets import DrugTemplateField, AutoCompleteWidget


class OutpatientPrescriptionForm(EventForm):
    """
    Form for creating and editing outpatient prescriptions.
    Extends the base EventForm with prescription-specific fields.
    """
    
    class Meta:
        model = OutpatientPrescription
        fields = ['patient', 'event_datetime', 'description', 'instructions', 'status', 'prescription_date']
        widgets = {
            'event_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'prescription_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Descrição breve da receita'
                }
            ),
            'instructions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Instruções gerais da receita (ex: tomar com água, em jejum, etc.)'
                }
            ),
            'status': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),
            'patient': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            )
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default prescription date to today
        if not self.instance.pk:
            self.fields['prescription_date'].initial = timezone.now().date()
        
        # Configure field labels and help texts
        self.fields['patient'].label = 'Paciente'
        self.fields['event_datetime'].label = 'Data e Hora'
        self.fields['description'].label = 'Descrição'
        self.fields['instructions'].label = 'Instruções Gerais'
        self.fields['status'].label = 'Status'
        self.fields['prescription_date'].label = 'Data da Receita'
        
        # Set help texts
        self.fields['instructions'].help_text = 'Instruções gerais que se aplicam a toda a receita'
        self.fields['description'].help_text = 'Descrição breve do motivo da prescrição'
        self.fields['prescription_date'].help_text = 'Data em que a receita será emitida'
    
    def save(self, commit=True):
        """Save the prescription with the current user as creator."""
        prescription = super().save(commit=False)
        
        if not prescription.pk and self.user:
            prescription.created_by = self.user
        
        if commit:
            prescription.save()
        
        return prescription


class PrescriptionItemForm(forms.ModelForm):
    """
    Form for individual prescription items.
    """
    
    drug_template = DrugTemplateField(
        label="Template de Medicamento",
        help_text="Selecione um template para preencher automaticamente os campos"
    )
    
    class Meta:
        model = PrescriptionItem
        fields = ['drug_name', 'presentation', 'usage_instructions', 'quantity', 'order', 'source_template']
        widgets = {
            'drug_name': AutoCompleteWidget(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nome do medicamento'
                }
            ),
            'presentation': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: 500mg comprimidos, 120ml xarope'
                }
            ),
            'usage_instructions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Ex: Tomar 1 comprimido de 8 em 8 horas por 7 dias'
                }
            ),
            'quantity': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: 21 comprimidos, 1 frasco'
                }
            ),
            'order': forms.HiddenInput(),
            'source_template': forms.HiddenInput()
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configure field labels
        self.fields['drug_name'].label = 'Medicamento'
        self.fields['presentation'].label = 'Apresentação'
        self.fields['usage_instructions'].label = 'Instruções de Uso'
        self.fields['quantity'].label = 'Quantidade'
        
        # Update drug template field with user context
        if self.user:
            self.fields['drug_template'] = DrugTemplateField(
                user=self.user,
                label="Template de Medicamento",
                help_text="Selecione um template para preencher automaticamente os campos"
            )
    
    def clean_order(self):
        """Ensure order is a positive integer."""
        order = self.cleaned_data.get('order')
        if order is None:
            return 1
        if order < 1:
            return 1
        return order


# Create the formset for prescription items
PrescriptionItemFormSet = inlineformset_factory(
    OutpatientPrescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=1,  # Start with one empty form
    min_num=1,  # Require at least one item
    validate_min=True,
    can_delete=True,
    fields=['drug_name', 'presentation', 'usage_instructions', 'quantity', 'order', 'source_template']
)


class PrescriptionItemFormSetHelper:
    """
    Helper class to provide additional functionality for the formset.
    """
    
    @staticmethod
    def get_formset_with_user(user, *args, **kwargs):
        """
        Create a formset instance with user context for drug template access.
        """
        class UserPrescriptionItemFormSet(PrescriptionItemFormSet):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Pass user to each form in the formset
                for form in self:
                    form.user = user
        
        return UserPrescriptionItemFormSet(*args, **kwargs)
    
    @staticmethod
    def prepare_formset_data(formset):
        """
        Prepare formset data for template rendering.
        Returns a dictionary with formset information.
        """
        return {
            'formset': formset,
            'management_form': formset.management_form,
            'empty_form': formset.empty_form,
            'can_delete': formset.can_delete,
        }