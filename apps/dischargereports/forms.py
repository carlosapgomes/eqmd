from django import forms
from django.utils import timezone
from .models import DischargeReport
from apps.events.models import Event


class HTML5DateTimeInput(forms.DateTimeInput):
    """Custom DateTimeInput that formats values correctly for HTML5 datetime-local inputs"""
    
    def format_value(self, value):
        if value is None:
            return ''
        if hasattr(value, 'astimezone'):
            # Convert to local timezone for display
            local_dt = value.astimezone(timezone.get_default_timezone())
            return local_dt.strftime('%Y-%m-%dT%H:%M')
        return str(value)


class HTML5DateInput(forms.DateInput):
    """Custom DateInput that formats values correctly for HTML5 date inputs"""
    
    def format_value(self, value):
        if value is None:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value)


class DischargeReportCreateForm(forms.ModelForm):
    """Form for creating new discharge reports"""

    class Meta:
        model = DischargeReport
        fields = [
            'event_datetime',
            'admission_date', 'discharge_date', 'medical_specialty',
            'admission_history', 'problems_and_diagnosis', 'exams_list',
            'procedures_list', 'inpatient_medical_history',
            'discharge_status', 'discharge_recommendations', 'is_draft'
        ]
        widgets = {
            'event_datetime': HTML5DateTimeInput(
                attrs={'class': 'form-control'}
            ),
            'admission_date': HTML5DateInput(
                attrs={'class': 'form-control'}
            ),
            'discharge_date': HTML5DateInput(
                attrs={'class': 'form-control'}
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

    def __init__(self, *args, **kwargs):
        # Extract patient from kwargs if provided
        self.patient = kwargs.pop("patient", None)
        super().__init__(*args, **kwargs)
        
        # Set input formats for datetime field
        self.fields["event_datetime"].input_formats = [
            "%Y-%m-%dT%H:%M",  # HTML5 datetime-local format
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        ]
        
        # Set default datetime to now if creating new instance
        if not self.instance.pk:
            utc_now = timezone.now().astimezone(timezone.get_default_timezone())
            self.fields["event_datetime"].initial = utc_now.strftime("%Y-%m-%dT%H:%M")
            
            # Auto-populate admission date if patient is provided
            if self.patient:
                self._set_admission_date_from_patient()
        else:
            # For existing instances, we need to format the data properly
            # This will be handled in the prepare_value method of custom widgets
            pass

    def _set_admission_date_from_patient(self):
        """
        Auto-populate admission_date from patient's latest active admission.
        Looks for the most recent PatientAdmission without a discharge_datetime.
        """
        try:
            from apps.patients.models import PatientAdmission
            
            # Find the latest active admission (no discharge date)
            latest_admission = PatientAdmission.objects.filter(
                patient=self.patient,
                discharge_datetime__isnull=True,
                is_active=True
            ).order_by('-admission_datetime').first()
            
            if latest_admission:
                # Set the admission date (date only, not datetime) in yyyy-MM-dd format
                admission_date = latest_admission.admission_datetime.date()
                self.fields["admission_date"].initial = admission_date.strftime("%Y-%m-%d")
                
                # Optionally also set today as discharge date since they're creating a discharge report
                today = timezone.now().date()
                self.fields["discharge_date"].initial = today.strftime("%Y-%m-%d")
                
        except Exception:
            # If anything goes wrong, silently continue without setting defaults
            pass

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

    def save(self, commit=True):
        """Override save to automatically set description to event type."""
        instance = super().save(commit=False)
        
        # Set description automatically to the discharge report event type
        instance.description = Event.EVENT_TYPE_CHOICES[Event.DISCHARGE_REPORT_EVENT][1]
        
        if commit:
            instance.save()
        return instance


class DischargeReportUpdateForm(forms.ModelForm):
    """Form for updating existing discharge reports"""

    class Meta:
        model = DischargeReport
        fields = [
            'event_datetime',
            'admission_date', 'discharge_date', 'medical_specialty',
            'admission_history', 'problems_and_diagnosis', 'exams_list',
            'procedures_list', 'inpatient_medical_history',
            'discharge_status', 'discharge_recommendations', 'is_draft'
        ]
        widgets = {
            'event_datetime': HTML5DateTimeInput(
                attrs={'class': 'form-control'}
            ),
            'admission_date': HTML5DateInput(
                attrs={'class': 'form-control'}
            ),
            'discharge_date': HTML5DateInput(
                attrs={'class': 'form-control'}
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


# For backward compatibility, keep the old form name
DischargeReportForm = DischargeReportCreateForm