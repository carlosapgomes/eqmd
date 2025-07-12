from django import forms
from django.core.exceptions import ValidationError
from .models import Patient, AllowedTag, Tag


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
    
    
    class Meta:
        model = Patient
        fields = ['name', 'birthday', 'id_number', 'fiscal_number', 'healthcard_number', 
                  'phone', 'address', 'city', 'state', 'zip_code', 'status', 
                  'bed']
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
        
        # Add CSS classes for styling
        self.fields['bed'].widget.attrs.update({
            'class': 'form-control bed-field'
        })

    def clean(self):
        """Custom validation for patient data"""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        
        # Clear bed field for outpatients and discharged patients
        if status in [Patient.Status.OUTPATIENT, Patient.Status.DISCHARGED]:
            cleaned_data['bed'] = ''
        
        return cleaned_data
    
    def is_valid(self):
        """Standard form validation"""
        return super().is_valid()
    

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