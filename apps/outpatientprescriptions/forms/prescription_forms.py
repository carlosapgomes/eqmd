from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from django.db import models
from apps.events.forms import EventForm
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.drugtemplates.models import DrugTemplate
from apps.outpatientprescriptions.widgets import DrugTemplateField, AutoCompleteWidget


class OutpatientPrescriptionForm(EventForm):
    """
    Form for creating and editing outpatient prescriptions.
    Extends the base EventForm with prescription-specific fields.
    """

    class Meta:
        model = OutpatientPrescription
        fields = [
            "patient",
            "event_datetime",
            "prescription_date",
            "instructions",
            "status",
        ]
        widgets = {
            "event_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "prescription_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "instructions": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Instruções gerais da receita (ex: uso oral, uso intramuscular.)",
                }
            ),
            "status": forms.RadioSelect(),
            "patient": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Set input formats for datetime field
        self.fields["event_datetime"].input_formats = [
            "%Y-%m-%dT%H:%M",  # HTML5 datetime-local format
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y %H:%M:%S",  # Format in error messages
            "%d/%m/%Y %H:%M",
        ]

        # Set input formats for prescription_date field
        self.fields["prescription_date"].input_formats = [
            "%Y-%m-%d",  # HTML5 date format
            "%d/%m/%Y",  # Format in error messages
        ]

        # Set default values for new instances
        if not self.instance.pk:
            utc_now = timezone.now().astimezone(timezone.get_default_timezone())
            self.fields["event_datetime"].initial = utc_now.strftime("%Y-%m-%dT%H:%M")
            self.fields["prescription_date"].initial = utc_now.strftime("%Y-%m-%d")
            # Set default status to draft for new instances
            self.fields["status"].initial = "draft"
        else:
            # Format existing instance datetime for HTML5 input
            dt = self.instance.event_datetime.astimezone(
                timezone.get_default_timezone()
            )
            self.fields["event_datetime"].initial = dt.strftime("%Y-%m-%dT%H:%M")
            # Format existing prescription_date for HTML5 input
            if self.instance.prescription_date:
                self.fields[
                    "prescription_date"
                ].initial = self.instance.prescription_date.strftime("%Y-%m-%d")

        # Configure field labels and help texts
        self.fields["patient"].label = "Paciente"
        self.fields["event_datetime"].label = "Data e Hora da Receita"
        self.fields["prescription_date"].label = "Data da Receita"
        self.fields["instructions"].label = "Instruções Gerais"
        self.fields["status"].label = "Status"

        # Set help texts
        # self.fields[
        #     "instructions"
        # ].help_text = "Instruções gerais que se aplicam a toda a receita"

        # Make instructions field not required
        self.fields["instructions"].required = False
        # self.fields[
        #     "event_datetime"
        # ].help_text = "Data e hora em que a receita está sendo emitida"
        # self.fields[
        #     "prescription_date"
        # ].help_text = "Data da receita para fins administrativos"

    def save(self, commit=True):
        """Save the prescription with the current user as creator."""
        prescription = super().save(commit=False)

        # Set description from event type choices
        from apps.events.models import Event

        prescription.description = Event.EVENT_TYPE_CHOICES[
            Event.OUTPT_PRESCRIPTION_EVENT
        ][1]

        if not prescription.pk and self.user:
            prescription.created_by = self.user

        # Automatically set prescription_date to the date part of event_datetime if not provided
        if prescription.event_datetime and not prescription.prescription_date:
            prescription.prescription_date = prescription.event_datetime.date()

        if commit:
            prescription.save()

        return prescription


class PrescriptionItemForm(forms.ModelForm):
    """
    Form for individual prescription items.
    """

    drug_template = DrugTemplateField(
        label="Template de Medicamento",
        help_text="Selecione um template para preencher automaticamente os campos",
    )

    class Meta:
        model = PrescriptionItem
        fields = [
            "drug_name",
            "presentation",
            "usage_instructions",
            "quantity",
            "order",
            "source_template",
        ]
        widgets = {
            "drug_name": AutoCompleteWidget(
                attrs={"class": "form-control", "placeholder": "Nome do medicamento"}
            ),
            "presentation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: 500mg comprimidos, 120ml xarope",
                }
            ),
            "usage_instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ex: Tomar 1 comprimido de 8 em 8 horas por 7 dias",
                }
            ),
            "quantity": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: 21 comprimidos, 1 frasco",
                }
            ),
            "order": forms.HiddenInput(),
            "source_template": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Configure field labels
        self.fields["drug_name"].label = "Medicamento"
        self.fields["presentation"].label = "Apresentação"
        self.fields["usage_instructions"].label = "Instruções de Uso"
        self.fields["quantity"].label = "Quantidade"
        self.fields["order"].label = "Ordem"

        # Update drug template field with user context
        if self.user:
            self.fields["drug_template"] = DrugTemplateField(
                user=self.user,
                label="Template de Medicamento",
                help_text="Selecione um template para preencher automaticamente os campos",
            )

    def clean_order(self):
        """Ensure order is a positive integer."""
        order = self.cleaned_data.get("order")
        if order is None:
            return 1
        if order < 1:
            return 1
        return order


# Create the formset for prescription items
PrescriptionItemFormSet = inlineformset_factory(
    OutpatientPrescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=0,  # No extra forms - min_num=1 ensures one form
    min_num=1,  # Require at least one item
    validate_min=True,
    can_delete=True,
    fields=[
        "drug_name",
        "presentation",
        "usage_instructions",
        "quantity",
        "order",
        "source_template",
    ],
)


class PrescriptionItemFormSetHelper:
    """
    Helper class to provide additional functionality for the formset.
    """

    @staticmethod
    def get_formset_with_user(user, *args, **kwargs):
        """
        Create a formset instance with user context for drug template access.
        """

        class UserPrescriptionItemFormSet(PrescriptionItemFormSet):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Pass user to each form in the formset
                for form in self:
                    form.user = user

        return UserPrescriptionItemFormSet(*args, **kwargs)

    @staticmethod
    def prepare_formset_data(formset):
        """
        Prepare formset data for template rendering.
        Returns a dictionary with formset information.
        """
        return {
            "formset": formset,
            "management_form": formset.management_form,
            "empty_form": formset.empty_form,
            "can_delete": formset.can_delete,
        }
