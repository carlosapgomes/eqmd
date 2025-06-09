from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
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
                    Column('status', css_class='col-md-4'),
                    Column('current_hospital', css_class='col-md-4'),
                    Column('bed', css_class='col-md-4'),
                ),
            ),
            Fieldset(
                'Tags',
                'tag_selection',
            ),
            Submit('submit', 'Salvar', css_class='btn btn-primary mt-3')
        )

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