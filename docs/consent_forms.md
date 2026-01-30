# Consent Forms

This guide explains how administrators create consent templates and how clinicians create and use consent form events.

## Admin: Create a Consent Template (Django Admin)

1) Open Django admin and go to **Termos de Consentimento**.
2) Click **Add** to create a new template.
3) Fill in:
   - **Name**
   - **Markdown do Termo** (the template body)
   - **Ativo** (toggle to make it selectable by clinicians)
4) Save the template.

If the template is invalid, the admin will display an error. The template must contain all required placeholders and only allowlisted placeholders.

### Allowed Placeholders

Use placeholders exactly as shown below:

- `{{ patient_name }}` (required)
- `{{ patient_record_number }}` (required)
- `{{ document_date }}` (required)
- `{{ procedure_description }}`

### Validation Rules

- All **required** placeholders must be present.
- **Unknown placeholders** are rejected.
- Rendering produces **immutable Markdown** stored on the consent event.

### Retire or Deactivate Templates

To retire a template, uncheck **Ativo** and save. Inactive templates are hidden from clinician selection but remain in admin for audit history.

## Clinician: Create a Consent Form (Patient Timeline)

1) Open the patient **Timeline**.
2) Click **Criar Evento**.
3) Under **Formulários PDF**, select **Termo de Consentimento**.
4) Complete the form:
   - **Paciente** (read-only)
   - **Prontuario** (read-only)
   - **Data do Documento** (defaults to today, editable)
   - **Descricao do Procedimento** (required)
5) Save. The system renders the selected template to an immutable Markdown snapshot and creates a timeline event.

## View and Download

- Open the consent event from the timeline to view the rendered Markdown.
- Use the **PDF** button to download a deterministic PDF generated from the stored Markdown snapshot.

## Optional Attachments (Scanned Documents)

Within the 24-hour edit window, the event creator can upload scanned files:

- Either **1 PDF**
- Or **1 to 3 images** (JPG, PNG, WEBP, HEIC)
- Mixed types are rejected.

Attachments are listed on the consent detail page.
