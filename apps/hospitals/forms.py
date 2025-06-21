from django import forms
from .models import Hospital, Ward


class HospitalForm(forms.ModelForm):
    class Meta:
        model = Hospital
        fields = [
            'name',
            'short_name', 
            'address',
            'city',
            'state',
            'zip_code',
            'phone'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o nome completo do hospital'
            }),
            'short_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: HSR, UFBA, etc.'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Endereço completo'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cidade'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '2',
                'placeholder': 'UF',
                'style': 'text-transform: uppercase;'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000'
            })
        }
        labels = {
            'name': 'Nome do Hospital',
            'short_name': 'Nome Curto',
            'address': 'Endereço',
            'city': 'Cidade',
            'state': 'Estado (UF)',
            'zip_code': 'CEP',
            'phone': 'Telefone'
        }
        help_texts = {
            'name': 'Nome oficial completo do hospital',
            'short_name': 'Sigla ou nome abreviado usado para identificação rápida',
            'state': 'Use apenas a sigla do estado (ex: BA, SP, RJ)',
            'zip_code': 'Formato: 00000-000',
            'phone': 'Inclua o código de área'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark required fields
        for field_name in ['name', 'short_name']:
            self.fields[field_name].required = True
            
    def clean_state(self):
        state = self.cleaned_data.get('state')
        if state:
            state = state.upper().strip()
            if len(state) > 2:
                raise forms.ValidationError('O estado deve ter apenas 2 caracteres (UF)')
        return state
    
    def clean_zip_code(self):
        zip_code = self.cleaned_data.get('zip_code')
        if zip_code:
            # Remove any non-digit characters except hyphen
            import re
            zip_code = re.sub(r'[^\d-]', '', zip_code)
            # Validate format
            if zip_code and not re.match(r'^\d{5}-?\d{3}$', zip_code):
                raise forms.ValidationError('CEP deve estar no formato 00000-000')
            # Add hyphen if missing
            if zip_code and '-' not in zip_code and len(zip_code) == 8:
                zip_code = f"{zip_code[:5]}-{zip_code[5:]}"
        return zip_code

    def save(self, commit=True):
        hospital = super().save(commit=False)
        if commit:
            hospital.save()
        return hospital


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ['name', 'description', 'hospital', 'capacity', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)