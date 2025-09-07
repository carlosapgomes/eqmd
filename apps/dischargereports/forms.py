from django import forms
from .models import DischargeReport


class DischargeReportForm(forms.ModelForm):
    """Form for discharge report create/update"""

    class Meta:
        model = DischargeReport
        fields = [
            'event_datetime', 'description',
            'admission_date', 'discharge_date', 'medical_specialty',
            'admission_history', 'problems_and_diagnosis', 'exams_list',
            'procedures_list', 'inpatient_medical_history',
            'discharge_status', 'discharge_recommendations', 'is_draft'
        ]
        widgets = {
            'event_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'description': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Descrição do relatório'}
            ),
            'admission_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'discharge_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'medical_specialty': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Ex: Cardiologia'}
            ),
            'admission_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'problems_and_diagnosis': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'exams_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'procedures_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'inpatient_medical_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 6}
            ),
            'discharge_status': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'discharge_recommendations': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'is_draft': forms.HiddenInput(),  # Hide from form, controlled by buttons
        }

    def clean(self):
        cleaned_data = super().clean()
        admission_date = cleaned_data.get('admission_date')
        discharge_date = cleaned_data.get('discharge_date')

        if admission_date and discharge_date:
            if admission_date > discharge_date:
                raise forms.ValidationError(
                    "A data de admissão deve ser anterior à data de alta."
                )

        return cleaned_data