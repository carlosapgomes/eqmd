from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.events.models import Event
from .models import ConsentForm, ConsentTemplate
from .services.renderer import render_template
from .validators import validate_consent_attachment_files


class ConsentFormCreateForm(forms.ModelForm):
    template = forms.ModelChoiceField(
        queryset=ConsentTemplate.objects.filter(is_active=True),
        label="Template",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    document_date = forms.DateField(
        label="Data do Documento",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control"},
            format="%Y-%m-%d",
        ),
    )
    procedure_description = forms.CharField(
        label="Descrição do Procedimento",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Descreva o procedimento...",
            }
        ),
    )

    class Meta:
        model = ConsentForm
        fields = ["template", "document_date", "procedure_description"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.patient = kwargs.pop("patient", None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["document_date"].initial = timezone.localdate().strftime(
                "%Y-%m-%d"
            )

        self.fields["document_date"].input_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]

    def clean_template(self):
        template = self.cleaned_data.get("template")
        if template and not template.is_active:
            raise ValidationError("Template inativo")
        return template

    def clean_document_date(self):
        document_date = self.cleaned_data.get("document_date")
        if document_date and document_date > timezone.localdate():
            raise ValidationError("A data do documento não pode ser no futuro.")
        return document_date

    def clean_procedure_description(self):
        description = self.cleaned_data.get("procedure_description", "")
        if not description or len(description.strip()) < 5:
            raise ValidationError("A descrição do procedimento é obrigatória.")
        return description

    def clean(self):
        cleaned_data = super().clean()
        if self.errors or not self.patient:
            return cleaned_data

        document_date = cleaned_data.get("document_date")
        template = cleaned_data.get("template")
        procedure_description = cleaned_data.get("procedure_description")
        if not (document_date and template and procedure_description):
            return cleaned_data

        record_number = self.patient.get_current_record_number() or "—"
        context = {
            "patient_name": self.patient.name,
            "patient_record_number": record_number,
            "document_date": document_date.strftime("%d/%m/%Y"),
            "procedure_description": procedure_description.strip(),
        }

        try:
            self._rendered_markdown = render_template(template.markdown_body, context)
        except ValidationError as exc:
            raise ValidationError(str(exc)) from exc

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.patient:
            raise ValidationError("Paciente não informado")

        instance.patient = self.patient
        instance.template = self.cleaned_data["template"]
        instance.document_date = self.cleaned_data["document_date"]
        instance.procedure_description = self.cleaned_data["procedure_description"].strip()
        instance.event_datetime = timezone.now()

        instance.rendered_markdown = getattr(self, "_rendered_markdown", None)
        if not instance.rendered_markdown:
            record_number = self.patient.get_current_record_number() or "—"
            context = {
                "patient_name": self.patient.name,
                "patient_record_number": record_number,
                "document_date": instance.document_date.strftime("%d/%m/%Y"),
                "procedure_description": instance.procedure_description,
            }
            instance.rendered_markdown = render_template(
                instance.template.markdown_body, context
            )
        instance.rendered_at = timezone.now()
        instance.description = f"Termo de Consentimento - {instance.template.name}"

        if self.user:
            if not instance.pk:
                instance.created_by = self.user
            instance.updated_by = self.user

        if commit:
            instance.save()
        return instance


def replace_document_date(markdown, source_date, target_date):
    """Replace the source's baked-in document date with the target date (D6).

    ``ConsentFormCreateForm`` renders ``document_date`` as ``dd/mm/aaaa`` into
    the markdown, so the prefill swaps that literal string once. Best-effort by
    design: if the source date does not appear verbatim the text is unchanged
    and the user adjusts it manually.
    """
    source_text = source_date.strftime("%d/%m/%Y")
    return markdown.replace(source_text, target_date.strftime("%d/%m/%Y"))


class ConsentFormDuplicateForm(forms.ModelForm):
    """Duplication form: a new consent form pre-filled from an existing one.

    The source's already-rendered markdown is exposed as an editable field so
    small corrections happen here, and the new document freezes that edited
    text at its own ``rendered_at`` (design D1). The template is a fixed
    provenance reference taken from the source, never from submitted input, so
    no template selector exists and no re-render happens (D2).
    """

    document_date = forms.DateField(
        label="Data do Documento",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control"},
            format="%Y-%m-%d",
        ),
    )
    procedure_description = forms.CharField(
        label="Descrição do Procedimento",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Descreva o procedimento...",
            }
        ),
    )
    markdown = forms.CharField(
        label="Markdown do Termo",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 20}),
    )

    class Meta:
        model = ConsentForm
        fields = [  # noqa: RUF012 — declarative ModelForm Meta attribute.
            "document_date",
            "procedure_description",
        ]

    def __init__(self, *args, **kwargs):
        self.source = kwargs.pop("source", None)
        self.user = kwargs.pop("user", None)
        self.patient = kwargs.pop("patient", None)
        super().__init__(*args, **kwargs)

        self.fields["document_date"].input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
        if not self.instance.pk:
            self.fields["document_date"].initial = timezone.localdate().strftime(
                "%Y-%m-%d"
            )

        if self.source is not None:
            self.fields["markdown"].initial = replace_document_date(
                self.source.rendered_markdown,
                self.source.document_date,
                timezone.localdate(),
            )
            self.fields[
                "procedure_description"
            ].initial = self.source.procedure_description

    def clean_document_date(self):
        document_date = self.cleaned_data.get("document_date")
        if document_date and document_date > timezone.localdate():
            raise ValidationError("A data do documento não pode ser no futuro.")
        return document_date

    def clean_procedure_description(self):
        description = self.cleaned_data.get("procedure_description", "")
        if not description or len(description.strip()) < 5:
            raise ValidationError("A descrição do procedimento é obrigatória.")
        return description

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.source is None:
            raise ValidationError("Termo de consentimento de origem não informado")
        if not self.patient:
            raise ValidationError("Paciente não informado")

        instance.patient = self.patient
        instance.template = self.source.template
        instance.document_date = self.cleaned_data["document_date"]
        instance.procedure_description = self.cleaned_data[
            "procedure_description"
        ].strip()
        instance.rendered_markdown = self.cleaned_data["markdown"]
        instance.rendered_at = timezone.now()
        instance.event_datetime = timezone.now()
        instance.event_type = Event.CONSENT_FORM_EVENT
        instance.description = f"Termo de Consentimento - {instance.template.name}"

        if self.user:
            if not instance.pk:
                instance.created_by = self.user
            instance.updated_by = self.user

        if commit:
            instance.save()
        return instance


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    def to_python(self, data):
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [super().to_python(item) for item in data]
        return [super().to_python(data)]

    def validate(self, data):
        if self.required and not data:
            raise ValidationError(self.error_messages["required"], code="required")


class ConsentAttachmentUploadForm(forms.Form):
    attachments = MultiFileField(
        label="Fotos do Termo Assinado",
        required=False,
        widget=MultiFileInput(
            attrs={"multiple": True, "class": "form-control", "accept": "image/*"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.existing_attachments = kwargs.pop("existing_attachments", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        files = self.files.getlist("attachments")
        if not files:
            raise ValidationError("Selecione pelo menos uma foto")

        file_type = validate_consent_attachment_files(
            files, existing_attachments=self.existing_attachments
        )
        cleaned_data["validated_files"] = files
        cleaned_data["attachment_kind"] = file_type
        return cleaned_data
