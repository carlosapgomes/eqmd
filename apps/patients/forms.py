from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Patient, AllowedTag, Tag, PatientRecordNumber, PatientAdmission, Ward
from .validators import validate_record_number_format


class FormSection:
    """Helper class for organizing form fields into medical sections"""
    
    def __init__(self, title, icon, fields, description=None):
        self.title = title
        self.icon = icon
        self.fields = fields
        self.description = description


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
        fields = ['name', 'birthday', 'gender', 'id_number', 'fiscal_number', 'healthcard_number', 
                  'phone', 'address', 'city', 'state', 'zip_code', 
                  'ward', 'bed']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'Nome completo do paciente',
                'aria-label': 'Nome do Paciente',
                'maxlength': '200'
            }),
            'birthday': forms.DateInput(attrs={
                'class': 'form-control form-control-medical',
                'type': 'date',
                'aria-label': 'Data de Nascimento'
            }, format='%Y-%m-%d'),
            'gender': forms.Select(attrs={
                'class': 'form-select form-control-medical',
                'aria-label': 'Sexo'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'RG ou documento de identidade',
                'aria-label': 'Documento de Identidade'
            }),
            'fiscal_number': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'CPF (xxx.xxx.xxx-xx)',
                'aria-label': 'CPF',
                'pattern': '[0-9]{3}\\.?[0-9]{3}\\.?[0-9]{3}-?[0-9]{2}',
                'maxlength': '14'
            }),
            'healthcard_number': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'Número da carteirinha do plano de saúde',
                'aria-label': 'Cartão de Saúde'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': '(00) 00000-0000',
                'aria-label': 'Telefone de Contato',
                'type': 'tel'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'Endereço completo',
                'aria-label': 'Endereço'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'Cidade',
                'aria-label': 'Cidade'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'Estado (UF)',
                'aria-label': 'Estado',
                'maxlength': '2'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': '00000-000',
                'aria-label': 'CEP',
                'pattern': '[0-9]{5}-?[0-9]{3}',
                'maxlength': '9'
            }),
            'ward': forms.Select(attrs={
                'class': 'form-select form-select-medical',
                'aria-label': 'Ala Hospitalar'
            }),
            'bed': forms.TextInput(attrs={
                'class': 'form-control form-control-medical',
                'placeholder': 'Número do leito',
                'aria-label': 'Leito'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set input formats for birthday field
        self.fields['birthday'].input_formats = [
            '%Y-%m-%d',  # HTML5 date format
            '%d/%m/%Y',  # Brazilian date format
        ]
        
        # Format existing birthday for HTML5 input
        if self.instance and self.instance.pk and self.instance.birthday:
            self.fields['birthday'].initial = self.instance.birthday.strftime('%Y-%m-%d')
        
        
        # Update record number widget for medical theme
        self.fields['initial_record_number'].widget.attrs.update({
            'class': 'form-control form-control-medical',
            'placeholder': 'Ex: REC001, 123456, etc.',
            'aria-label': 'Número do Prontuário Inicial'
        })

    def get_form_sections(self):
        """Return form fields organized into medical sections"""
        return [
            FormSection(
                title="Informações Básicas",
                icon="bi-person-fill",
                fields=[
                    ('name', self['name']),
                    ('birthday', self['birthday']),
                    ('gender', self['gender']),
                ],
                description="Dados pessoais essenciais do paciente"
            ),
            FormSection(
                title="Documentos & Identificação",
                icon="bi-card-checklist",
                fields=[
                    ('id_number', self['id_number']),
                    ('fiscal_number', self['fiscal_number']),
                    ('healthcard_number', self['healthcard_number']),
                ],
                description="Documentos oficiais para identificação do paciente"
            ),
            FormSection(
                title="Informações de Contato",
                icon="bi-telephone",
                fields=[
                    ('phone', self['phone']),
                    ('address', self['address']),
                    ('city', self['city']),
                    ('state', self['state']),
                    ('zip_code', self['zip_code']),
                ],
                description="Informações para contato e localização"
            ),
            FormSection(
                title="Status Hospitalar",
                icon="bi-hospital",
                fields=[
                    ('ward', self['ward']),
                    ('bed', self['bed']),
                ],
                description="Informações sobre a localização atual no hospital"
            ),
        ]

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
    admission_datetime = forms.DateTimeField(
        required=True,
        label="Data/Hora da Internação",
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    admission_type = forms.ChoiceField(
        choices=PatientAdmission.AdmissionType.choices,
        required=True,
        label="Tipo de Internação",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
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
    discharge_datetime = forms.DateTimeField(
        required=True,
        label="Data/Hora da Alta",
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    discharge_type = forms.ChoiceField(
        choices=PatientAdmission.DischargeType.choices,
        required=True,
        label="Tipo de Alta",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
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


class InternalTransferForm(StatusChangeForm):
    """Form for internal ward/bed transfers"""
    ward = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=True,
        label="Nova Ala",
        empty_label="Selecione uma ala...",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    bed = forms.CharField(
        max_length=20,
        required=False,
        label="Novo Leito",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 101A, UTI-02, etc.'
        })
    )
    transfer_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo da transferência interna...'
        }),
        required=True,
        label="Motivo da Transferência"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Ward
        self.fields['ward'].queryset = Ward.objects.filter(is_active=True).order_by('name')


class TransferPatientForm(StatusChangeForm):
    """Form for transferring patients (external - deprecated)"""
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


class EditAdmissionForm(forms.ModelForm):
    """Form for editing admission data only"""
    
    class Meta:
        model = PatientAdmission
        fields = [
            'admission_datetime', 'admission_type', 'initial_bed',
            'ward', 'admission_diagnosis'
        ]
        widgets = {
            'admission_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'admission_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'initial_bed': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: A101, UTI-02, etc.'
            }),
            'ward': forms.Select(attrs={
                'class': 'form-select'
            }),
            'admission_diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Diagnóstico principal da internação...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter only active wards
        self.fields['ward'].queryset = Ward.objects.filter(is_active=True)
        self.fields['ward'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Prevent editing discharge fields for admission-only form
        if getattr(self.instance, 'discharge_datetime', None):
            raise ValidationError("Não é possível editar dados de internação após a alta")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        return instance


class EditDischargeForm(forms.ModelForm):
    """Form for editing discharge data only"""
    
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
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure this is only used for discharged admissions
        if not getattr(self.instance, 'discharge_datetime', None):
            raise ValidationError("Não é possível editar dados de alta de internação ativa")
        
        # Ensure discharge datetime is not before admission datetime
        discharge_datetime = cleaned_data.get('discharge_datetime')
        if discharge_datetime and self.instance.admission_datetime:
            if discharge_datetime < self.instance.admission_datetime:
                raise ValidationError("Data de alta não pode ser anterior à data de internação")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        return instance