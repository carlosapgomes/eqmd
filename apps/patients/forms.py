from django import forms
from django.core.exceptions import ValidationError
from .models import Patient, PatientHospitalRecord, AllowedTag, Tag


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


class PatientHospitalRecordNestedForm(forms.ModelForm):
    """Nested form for hospital record data within patient form"""
    class Meta:
        model = PatientHospitalRecord
        fields = ['hospital', 'record_number', 'first_admission_date', 
                  'last_admission_date', 'last_discharge_date']
        widgets = {
            'first_admission_date': forms.DateInput(attrs={'type': 'date'}),
            'last_admission_date': forms.DateInput(attrs={'type': 'date'}),
            'last_discharge_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for nested form
        for field in self.fields.values():
            field.required = False
        
        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class PatientForm(forms.ModelForm):
    # Include tag selection in the form
    tag_selection = forms.ModelMultipleChoiceField(
        queryset=AllowedTag.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags",
        help_text="Selecione as tags aplicáveis para este paciente"
    )
    
    # Hospital record management flags
    create_hospital_record = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = Patient
        fields = ['name', 'birthday', 'id_number', 'fiscal_number', 'healthcard_number', 
                  'phone', 'address', 'city', 'state', 'zip_code', 'status', 
                  'current_hospital', 'bed']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Extract hospital record data if provided
        hospital_record_data = kwargs.pop('hospital_record_data', None)
        super().__init__(*args, **kwargs)
        
        # Set initial values for tag selection if editing existing patient
        if self.instance and self.instance.pk:
            self.fields['tag_selection'].initial = [
                tag.allowed_tag for tag in self.instance.tags.all()
            ]
        
        # Add help text for hospital field
        self.fields['current_hospital'].help_text = (
            'Obrigatório apenas para pacientes internados, em emergência ou transferidos. '
            'Pacientes ambulatoriais não precisam de hospital atual.'
        )
        
        # Add CSS classes for conditional display
        self.fields['current_hospital'].widget.attrs.update({
            'class': 'form-control hospital-field'
        })
        self.fields['bed'].widget.attrs.update({
            'class': 'form-control bed-field'
        })
        
        # Initialize nested hospital record form
        self.hospital_record_form = PatientHospitalRecordNestedForm(
            data=hospital_record_data,
            prefix='hospital_record'
        )

    def clean(self):
        """Custom validation to ensure hospital is provided when required"""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        current_hospital = cleaned_data.get('current_hospital')
        
        # Check if hospital is required for this status
        if status in [Patient.Status.INPATIENT, Patient.Status.EMERGENCY, Patient.Status.TRANSFERRED]:
            if not current_hospital:
                raise forms.ValidationError({
                    'current_hospital': f'Hospital é obrigatório para pacientes com status "{Patient.Status(status).label}"'
                })
        
        # Clear hospital-related fields for outpatients and discharged
        if status in [Patient.Status.OUTPATIENT, Patient.Status.DISCHARGED]:
            cleaned_data['current_hospital'] = None
            cleaned_data['bed'] = ''
        
        return cleaned_data
    
    def is_valid(self):
        """Override to include hospital record form validation"""
        valid = super().is_valid()
        
        # Only validate hospital record form if it has data
        if self.hospital_record_form.has_changed():
            hospital_record_valid = self.hospital_record_form.is_valid()
            valid = valid and hospital_record_valid
        
        return valid
    
    def clean_hospital_record_data(self):
        """Validate hospital record data if provided"""
        if not self.hospital_record_form.has_changed():
            return None
        
        if not self.hospital_record_form.is_valid():
            raise ValidationError("Hospital record data is invalid")
        
        hospital_record_data = self.hospital_record_form.cleaned_data
        
        # If hospital is provided, require record number
        if hospital_record_data.get('hospital') and not hospital_record_data.get('record_number'):
            raise ValidationError({
                'hospital_record-record_number': 'Número de registro é obrigatório quando hospital é selecionado'
            })
        
        return hospital_record_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
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
            
            # Handle hospital record creation/update
            if self.hospital_record_form.has_changed() and self.hospital_record_form.is_valid():
                hospital_record_data = self.hospital_record_form.cleaned_data
                hospital = hospital_record_data.get('hospital')
                
                if hospital:  # Only create/update if hospital is selected
                    hospital_record, created = PatientHospitalRecord.objects.get_or_create(
                        patient=instance,
                        hospital=hospital,
                        defaults={
                            'record_number': hospital_record_data.get('record_number', ''),
                            'first_admission_date': hospital_record_data.get('first_admission_date'),
                            'last_admission_date': hospital_record_data.get('last_admission_date'),
                            'last_discharge_date': hospital_record_data.get('last_discharge_date'),
                            'created_by': current_user,
                            'updated_by': current_user,
                        }
                    )
                    
                    if not created:
                        # Update existing record
                        if hospital_record_data.get('record_number'):
                            hospital_record.record_number = hospital_record_data['record_number']
                        if hospital_record_data.get('first_admission_date'):
                            hospital_record.first_admission_date = hospital_record_data['first_admission_date']
                        if hospital_record_data.get('last_admission_date'):
                            hospital_record.last_admission_date = hospital_record_data['last_admission_date']
                        if hospital_record_data.get('last_discharge_date'):
                            hospital_record.last_discharge_date = hospital_record_data['last_discharge_date']
                        hospital_record.updated_by = current_user
                        hospital_record.save()
                        
        return instance


class PatientHospitalRecordForm(forms.ModelForm):
    class Meta:
        model = PatientHospitalRecord
        fields = ['patient', 'hospital', 'record_number', 'first_admission_date', 
                  'last_admission_date', 'last_discharge_date']
        widgets = {
            'first_admission_date': forms.DateInput(attrs={'type': 'date'}),
            'last_admission_date': forms.DateInput(attrs={'type': 'date'}),
            'last_discharge_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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