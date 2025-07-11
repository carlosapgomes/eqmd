# Code Analysis for Outpatient Prescription System After its Implementation

## Initial Implementation Plan and Tasks that were designed to be implemented

Read the file @prompts/outprescriptons/implementation_plan.md to learn about the initial implementation plan.
Read the files at @.taskmaster/tasks/ to learn about the tasks that were created based on the initial implementation plan and that are supposed to be implemented.

## Current State

### Drug Templates App

- **Models**:
  - `DrugTemplate` model is well-defined with all required fields and proper validation
  - `PrescriptionTemplate` and `PrescriptionTemplateItem` models are implemented with necessary fields and relationships
  - Models include indexes for performance optimization

What a DrugTemplate represents:

- A drug template represents a specific medication with its details such as template name (e.g., "Paracetamol 500mg Comprimidos"), drug name, presentation, usage instructions, total amount usually prescribed (e.g., "30 comprimidos" ), and creator.
- It serves as a blueprint for prescribing medications, allowing users to quickly add commonly used drugs to their prescriptions.
- Drug templates can be public or private, depending on the `is_public` field.
- The `usage_count` field tracks how many times a template has been used in prescriptions.

What a PrescriptionTemplate represents:

- A prescription template represents an example of a full outpatient prescription that can be duplicated to be used as an OutpatientPrescription by multiple patients. Because of that I am not sure if both this template and the PrescriptionTemplateItem should be part of the DrugTemplates app, or if it should be part of the OutpatientPrescriptions app.
- It contains a collection of `PrescriptionTemplateItem` objects, that may be a copy of `DrugTemplate` objects, or just free-text entries, each representing a specific medication with the same details as a drug template (drug name, presentation, usage instructions, quantity, order in which it should appear in the prescription).
- Prescription templates can be public or private, depending on the `is_public` field.
- The `usage_count` field tracks how many times a template has been used in prescriptions.

What a PrescriptionTemplateItem represents:

- A prescription template item represents a medication within a prescription template.
- It contains the same fields as a drug template (drug name, presentation, usage instructions, quantity, order).
- It has a foreign key to the `PrescriptionTemplate` it belongs to.
- It does not have its own `created_at` and `updated_at` fields, as it inherits them from the `PrescriptionTemplate` it belongs to.
- It is created when a user adds a medication to a prescription template, and is deleted when the prescription template is deleted.
- A user never edits a `PrescriptionTemplateItem` directly, but rather edits the `PrescriptionTemplate` it belongs to.

### Outpatient Prescriptions App

- **Models**:
  - `OutpatientPrescription` model extends `Event` correctly with `event_type=7` and represents an outpatient prescription with additional fields for instructions, status, and prescription date and have a relationship with a list of `PrescriptionItem` objects.
  - `PrescriptionItem` model is implemented with necessary fields and relationships and represents a medication within an outpatient prescription with a foreign key to the `OutpatientPrescription` it belongs to, and all fields that a `PrescriptionTemplateItem` has.
  - `PrescriptionItem` does not have its own `created_at` and `updated_at` fields, as it inherits them from the `OutpatientPrescription` it belongs to.
  - It is created when a user adds a medication to a prescription template, and is deleted when the prescription template is deleted.
  - A user never edits a `PrescriptionItem` directly, but rather edits the `OutpatientPrescription` it belongs to.
  - Models include indexes for performance optimization
  - When a PrescriptionTemplate is used to create an OutpatientPrescription, the `usage_count` field of the PrescriptionTemplate is incremented, all `PrescriptionTemplateItem` objects are copied to `PrescriptionItem` objects. No relationship is created between the `PrescriptionItem` and the `PrescriptionTemplateItem` objects.

### Desired Behavior

The system should allow users to:

- Create and manage drug templates they created
- Create outpatient prescriptions using drug templates or duplicating prescription templates. After duplicating a PrescriptionTemplate, the user should be able to edit the medication list and instructions as needed for the specific patient.
- Generate printable documents for prescriptions

### Your Mission

I think the current state of those apps does not fully meet the requirements.

Please, check the current implementation and provide a report on its current state and if it meets the requirements and the desired behavior above.

Please, provide a list of recommendations on how to improve the current implementation to meet the requirements and the desired behavior, but do not write any code yet, just show me your thoughts and recommendations.
