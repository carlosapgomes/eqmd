import re
from django import forms
from .models import MatrixUserBinding


class MatrixBindingForm(forms.ModelForm):
    """Form for creating Matrix bindings."""
    
    class Meta:
        model = MatrixUserBinding
        fields = ['matrix_id']
        widgets = {
            'matrix_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@usuario:servidor.com'
            })
        }
    
    def clean_matrix_id(self):
        matrix_id = self.cleaned_data['matrix_id'].strip()
        
        # Validate Matrix ID format: @localpart:domain
        pattern = r'^@[a-zA-Z0-9._=\-/]+:[a-zA-Z0-9.\-]+$'
        if not re.match(pattern, matrix_id):
            raise forms.ValidationError(
                'ID Matrix inválido. Use o formato @usuario:servidor.com'
            )
        
        return matrix_id