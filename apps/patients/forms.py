from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div
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
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True


class PatientForm(forms.ModelForm):
    # Include tag selection in the form
    tag_selection = forms.ModelMultipleChoiceField(
        queryset=AllowedTag.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags",
        help_text="Selecione as tags aplicáveis para este paciente"
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
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Informações do Paciente',
                Row(
                    Column('name', css_class='col-md-6'),
                    Column('birthday', css_class='col-md-6'),
                ),
                Row(
                    Column('id_number', css_class='col-md-4'),
                    Column('fiscal_number', css_class='col-md-4'),
                    Column('healthcard_number', css_class='col-md-4'),
                ),
                Row(
                    Column('phone', css_class='col-md-12'),
                ),
            ),
            Fieldset(
                'Informações de Endereço',
                Row(
                    Column('address', css_class='col-md-8'),
                    Column('zip_code', css_class='col-md-4'),
                ),
                Row(
                    Column('city', css_class='col-md-6'),
                    Column('state', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Informações Hospitalares',
                Row(
                    Column('status', css_class='col-md-12'),
                ),
                Div(
                    Row(
                        Column('current_hospital', css_class='col-md-8'),
                        Column('bed', css_class='col-md-4'),
                    ),
                    css_class='hospital-fields-container',
                    css_id='hospital-fields'
                ),
                HTML("""
                    <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const statusField = document.querySelector('#id_status');
                        const hospitalFieldsContainer = document.querySelector('#hospital-fields');
                        const hospitalField = document.querySelector('#id_current_hospital');
                        const bedField = document.querySelector('#id_bed');
                        
                        function toggleHospitalFields() {
                            const status = statusField.value;
                            const requiresHospital = ['2', '3', '5']; // INPATIENT, EMERGENCY, TRANSFERRED
                            
                            if (requiresHospital.includes(status)) {
                                hospitalFieldsContainer.style.display = 'block';
                                hospitalField.required = true;
                            } else {
                                hospitalFieldsContainer.style.display = 'none';
                                hospitalField.required = false;
                                hospitalField.value = '';
                                bedField.value = '';
                            }
                        }
                        
                        // Initial toggle
                        toggleHospitalFields();
                        
                        // Toggle on status change
                        statusField.addEventListener('change', toggleHospitalFields);
                    });
                    </script>
                """)
            ),
            Fieldset(
                'Tags',
                'tag_selection',
            ),
            Submit('submit', 'Salvar', css_class='btn btn-primary mt-3')
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
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Registro Hospitalar',
                Row(
                    Column('patient', css_class='col-md-6'),
                    Column('hospital', css_class='col-md-6'),
                ),
                'record_number',
                Row(
                    Column('first_admission_date', css_class='col-md-4'),
                    Column('last_admission_date', css_class='col-md-4'),
                    Column('last_discharge_date', css_class='col-md-4'),
                ),
            ),
            Submit('submit', 'Salvar', css_class='btn btn-primary mt-3')
        )


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
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Informações da Tag',
                'name',
                'description',
                Row(
                    Column('color', css_class='col-md-6'),
                    Column('is_active', css_class='col-md-6'),
                ),
            ),
            Submit('submit', 'Salvar', css_class='btn btn-primary mt-3')
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance