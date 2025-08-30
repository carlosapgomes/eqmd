"""
Forms for core user lifecycle management
"""
from django import forms


class SimplifiedAccountRenewalForm(forms.Form):
    """Simplified form for users to request account renewal"""
    
    current_position = forms.CharField(
        max_length=200,
        label="Posição/Cargo Atual",
        help_text="Seu cargo ou posição atual na instituição",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Médico Residente, Enfermeiro, Estudante de Medicina'
        })
    )
    
    supervisor_name = forms.CharField(
        max_length=200,
        label="Nome do Supervisor",
        help_text="Nome do seu supervisor direto",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome completo do supervisor'
        })
    )
    
    supervisor_email = forms.EmailField(
        label="Email do Supervisor",
        help_text="Email do supervisor para confirmação",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email.supervisor@hospital.com'
        })
    )
    
    renewal_reason = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Descreva o motivo para renovação do acesso...'
        }),
        label="Motivo da Renovação",
        help_text="Explique por que precisa renovar o acesso ao sistema (máximo 500 caracteres)"
    )
    
    expected_duration = forms.ChoiceField(
        choices=[
            ('3', '3 meses'),
            ('6', '6 meses'),
            ('12', '1 ano'),
            ('24', '2 anos'),
        ],
        label="Duração Esperada",
        help_text="Por quanto tempo espera precisar do acesso",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
    
    def save(self):
        """Create renewal request record"""
        from .models import AccountRenewalRequest
        
        return AccountRenewalRequest.objects.create(
            user=self.user,
            current_position=self.cleaned_data['current_position'],
            supervisor_name=self.cleaned_data['supervisor_name'],
            supervisor_email=self.cleaned_data['supervisor_email'],
            renewal_reason=self.cleaned_data['renewal_reason'],
            expected_duration_months=int(self.cleaned_data['expected_duration']),
            status='pending',
        )