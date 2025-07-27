from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Patient, AllowedTag, Tag, PatientRecordNumber, PatientAdmission, Ward
from .validators import validate_record_number_format


class TagCreationForm(forms.Form):
    """Form for creating tags from allowed tags"""
    allowed_tags = forms.ModelMultipleChoiceField(
        queryset=AllowedTag.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)




class PatientForm(forms.ModelForm):
    # Include tag selection in the form
    tag_selection = forms.ModelMultipleChoiceField(
        queryset=AllowedTag.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags",
        help_text="Selecione as tags aplicáveis para este paciente"
    )
    
    # Add record number field to patient form
    initial_record_number = forms.CharField(
        max_length=50,
        required=False,
        label="Número do Prontuário",
        help_text="Número inicial do prontuário (pode ser alterado posteriormente)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: REC001, 123456, etc.'
        })
    )
    
    class Meta:
        model = Patient
        fields = ['name', 'birthday', 'id_number', 'fiscal_number', 'healthcard_number', 
                  'phone', 'address', 'city', 'state', 'zip_code', 
                  'ward', 'bed']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'ward': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for tag selection if editing existing patient
        if self.instance and self.instance.pk:
            self.fields['tag_selection'].initial = [
                tag.allowed_tag for tag in self.instance.tags.all()
            ]
        
        # Add CSS classes for styling
        self.fields['bed'].widget.attrs.update({
            'class': 'form-control bed-field'
        })

    def clean(self):
        """Custom validation for patient data"""
        cleaned_data = super().clean()
        # Note: Status field removed from form - status changes now handled 
        # through dedicated status change actions in patient detail page
        return cleaned_data
    
    def is_valid(self):
        """Standard form validation"""
        return super().is_valid()
    

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            
            # Handle initial record number if provided
            initial_record_number = self.cleaned_data.get('initial_record_number')
            if initial_record_number and not instance.record_numbers.exists():
                current_user = getattr(self, 'current_user', instance.updated_by)
                PatientRecordNumber.objects.create(
                    patient=instance,
                    record_number=initial_record_number,
                    change_reason="Número inicial do prontuário",
                    effective_date=timezone.now(),
                    created_by=current_user,
                    updated_by=current_user
                )
            
            # Handle tag selection
            selected_allowed_tags = self.cleaned_data.get('tag_selection', [])
            
            # Clear existing tags
            instance.tags.clear()
            
            # Create new tag instances for selected allowed tags
            current_user = getattr(self, 'current_user', instance.updated_by)
            for allowed_tag in selected_allowed_tags:
                tag, created = Tag.objects.get_or_create(
                    allowed_tag=allowed_tag,
                    defaults={
                        'created_by': current_user,
                        'updated_by': current_user,
                    }
                )
                instance.tags.add(tag)
                        
        return instance




class AllowedTagForm(forms.ModelForm):
    class Meta:
        model = AllowedTag
        fields = ['name', 'description', 'color', 'is_active']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class PatientRecordNumberForm(forms.ModelForm):
    """Form for creating/updating patient record numbers"""
    
    class Meta:
        model = PatientRecordNumber
        fields = ['record_number', 'change_reason', 'effective_date']
        widgets = {
            'record_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: REC001, 123456, etc.'
            }),
            'change_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motivo da alteração do número do prontuário...'
            }),
            'effective_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default effective date to now
        if not self.instance.pk:
            self.fields['effective_date'].initial = timezone.now()
    
    def clean_record_number(self):
        record_number = self.cleaned_data.get('record_number')
        if record_number:
            validate_record_number_format(record_number)
        return record_number
    
    def clean_effective_date(self):
        effective_date = self.cleaned_data.get('effective_date')
        if effective_date and effective_date > timezone.now():
            raise ValidationError("Data de vigência não pode ser no futuro")
        return effective_date
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.patient:
            instance.patient = self.patient
        if self.user:
            instance.created_by = self.user
            instance.updated_by = self.user
        
        # Always set as current when creating new record
        if not instance.pk:
            instance.is_current = True
            
            # Get previous record number for history
            current_record = self.patient.record_numbers.filter(is_current=True).first()
            if current_record:
                instance.previous_record_number = current_record.record_number
        
        if commit:
            instance.save()
        return instance


class QuickRecordNumberUpdateForm(forms.Form):
    """Quick form for updating just the record number"""
    
    record_number = forms.CharField(
        max_length=50,
        label="Novo Número do Prontuário",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o novo número...'
        })
    )
    change_reason = forms.CharField(
        required=False,
        label="Motivo (opcional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Motivo da alteração...'
        })
    )
    
    def clean_record_number(self):
        record_number = self.cleaned_data.get('record_number')
        if record_number:
            validate_record_number_format(record_number)
        return record_number


class PatientAdmissionForm(forms.ModelForm):
    """Form for creating patient admissions"""
    
    class Meta:
        model = PatientAdmission
        fields = [
            'admission_datetime', 'admission_type', 
            'ward', 'initial_bed', 'admission_diagnosis'
        ]
        widgets = {
            'admission_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'admission_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'ward': forms.Select(attrs={
                'class': 'form-select'
            }),
            'initial_bed': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: A101, UTI-02, etc.'
            }),
            'admission_diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Diagnóstico principal da admissão...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter only active wards
        self.fields['ward'].queryset = Ward.objects.filter(is_active=True)
        # Make ward required for admissions
        self.fields['ward'].required = True
        
        # Set default admission time to now
        if not self.instance.pk:
            self.fields['admission_datetime'].initial = timezone.now()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if patient is already admitted
        if self.patient and self.patient.is_currently_admitted():
            raise ValidationError("Paciente já está internado")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.patient:
            instance.patient = self.patient
        if self.user:
            instance.created_by = self.user
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        return instance


class PatientDischargeForm(forms.ModelForm):
    """Form for discharging patients"""
    
    class Meta:
        model = PatientAdmission
        fields = [
            'discharge_datetime', 'discharge_type', 'final_bed',
            'discharge_diagnosis'
        ]
        widgets = {
            'discharge_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'discharge_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'final_bed': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: A101, UTI-02, etc.'
            }),
            'discharge_diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Diagnóstico final e condições da alta...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default discharge time to now
        if not self.instance.discharge_datetime:
            self.fields['discharge_datetime'].initial = timezone.now()
        
        # Pre-fill final bed with initial bed
        if self.instance.initial_bed and not self.instance.final_bed:
            self.fields['final_bed'].initial = self.instance.initial_bed
    
    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance.can_discharge():
            raise ValidationError("Esta internação não pode ser finalizada")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        return instance


class QuickAdmissionForm(forms.Form):
    """Quick admission form for common scenarios"""
    
    admission_type = forms.ChoiceField(
        choices=PatientAdmission.AdmissionType.choices,
        label="Tipo de Admissão",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    initial_bed = forms.CharField(
        max_length=20,
        required=False,
        label="Leito",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: A101, UTI-02, etc.'
        })
    )
    admission_diagnosis = forms.CharField(
        required=False,
        label="Diagnóstico",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Diagnóstico principal...'
        })
    )


class QuickDischargeForm(forms.Form):
    """Quick discharge form for common scenarios"""
    
    discharge_type = forms.ChoiceField(
        choices=PatientAdmission.DischargeType.choices,
        label="Tipo de Alta",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    discharge_diagnosis = forms.CharField(
        required=False,
        label="Diagnóstico de Alta",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Condições da alta...'
        })
    )


class WardForm(forms.ModelForm):
    """Form for creating and editing wards"""
    
    class Meta:
        model = Ward
        fields = [
            'name', 'abbreviation', 'description', 'floor', 
            'capacity_estimate', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'floor': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity_estimate': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Status Change Forms

class StatusChangeForm(forms.Form):
    """Base form for status changes"""
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo da alteração de status...'
        }),
        required=False,
        label="Motivo da Alteração"
    )


class AdmitPatientForm(StatusChangeForm):
    """Form for admitting patients (changing to inpatient status)"""
    ward = forms.ModelChoiceField(
        queryset=Ward.objects.filter(is_active=True),
        required=True,
        label="Ala",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    bed = forms.CharField(
        max_length=20, 
        required=False,
        label="Leito",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: A101, UTI-02, etc.'
        })
    )


class DischargePatientForm(StatusChangeForm):
    """Form for discharging patients"""
    discharge_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo específico da alta...'
        }),
        required=True,
        label="Motivo da Alta"
    )


class EmergencyAdmissionForm(StatusChangeForm):
    """Form for emergency admissions"""
    ward = forms.ModelChoiceField(
        queryset=Ward.objects.filter(is_active=True),
        required=False,
        label="Ala",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    bed = forms.CharField(
        max_length=20, 
        required=False,
        label="Leito",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: PS-01, URG-02, etc.'
        })
    )


class TransferPatientForm(StatusChangeForm):
    """Form for transferring patients"""
    destination = forms.CharField(
        max_length=200,
        required=True,
        label="Destino da Transferência",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Hospital ou unidade de destino...'
        })
    )


class DeclareDeathForm(StatusChangeForm):
    """Form for declaring patient death"""
    death_time = forms.DateTimeField(
        required=True,
        label="Hora do Óbito",
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Causa do óbito...'
        }),
        required=True,
        label="Causa do Óbito"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default death time to now
        self.fields['death_time'].initial = timezone.now()


class SetOutpatientForm(StatusChangeForm):
    """Form for setting patient to outpatient status"""
    follow_up_date = forms.DateField(
        required=False,
        label="Data de Retorno",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    follow_up_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Orientações para acompanhamento ambulatorial...'
        }),
        required=False,
        label="Orientações de Acompanhamento"
    )