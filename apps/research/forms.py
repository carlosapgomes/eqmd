from django import forms

class ClinicalSearchForm(forms.Form):
    """
    Form for clinical research full text search.
    """
    query = forms.CharField(
        max_length=200,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite os termos de busca (ex: diabetes, hipertensão, medicação)',
            'autocomplete': 'off'
        }),
        label='Busca Clínica',
        help_text='Digite pelo menos 3 caracteres para buscar nas evoluções diárias'
    )

    def clean_query(self):
        query = self.cleaned_data.get('query')
        if query:
            query = ' '.join(query.split())  # Remove extra whitespace
        return query