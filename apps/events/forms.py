from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['event_type', 'event_datetime', 'description', 'patient']
        widgets = {
            'event_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-primary'))

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        self.helper.layout = Layout(
            Row(
                Column('event_type', css_class='form-group col-md-6 mb-0'),
                Column('event_datetime', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            'patient',
        )