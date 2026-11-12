# Slice 01 - Hide emergency status action button from patient profile

Goal:
Remove the `Emergência` action button (and its orphaned modal) from the
patient profile's "Status & Gerenciamento de Internação" section without
touching any backend functionality (view, URL, form, signals all stay).

Scope boundaries:

- Included: the template tag `available_status_actions` in
  `apps/patients/templatetags/patient_tags.py` stops offering the
  `Patient.Status.EMERGENCY` transition; the `emergency_admissionModal` block
  is removed from `apps/patients/templates/patients/partials/admission_section.html`;
  the affected template tag tests are updated to the new contract.
- Excluded (explicit constraint): `EmergencyAdmissionView`,
  `EmergencyAdmissionForm`, the URL name `emergency_admission`, signals,
  permissions, and their tests (`test_status_changes.py`, `test_forms.py`) —
  these must keep passing without any modification.
- Excluded (explicit constraint): the "Emergência" option in the patient list
  status filter (`patient_list.html`), the `patient_status_badge` emergency
  badge, the "Paciente em Emergência" alert, and the "Emergência" option under
  "Tipo de Internação" in the admit modal (different concept: admission type).
- Explicit constraint: hide by removing the EMERGENCY tuple from the single
  generation point (`status_transitions`); do NOT hide via CSS or template
  conditionals.
- Explicit constraint: no database migrations, no model changes.

Files to create/modify:

- `apps/patients/templatetags/patient_tags.py`
- `apps/patients/templates/patients/partials/admission_section.html`
- `apps/patients/tests/test_status_template_tags.py`

Tests to write FIRST (TDD):

- Update `test_available_status_actions_outpatient` in
  `apps/patients/tests/test_status_template_tags.py`: replace
  `self.assertIn(Patient.Status.EMERGENCY, action_statuses)` with
  `self.assertNotIn(Patient.Status.EMERGENCY, action_statuses)` and keep the
  assertions that INPATIENT, DISCHARGED and DECEASED remain present
  (regression guard).
- Update `test_available_status_actions_inpatient` to also assert
  `self.assertNotIn(Patient.Status.EMERGENCY, action_statuses)`.

Implementation steps:

1. Update the two tests above and run them — they must FAIL (red) while the
   EMERGENCY tuple still exists in `status_transitions`.
2. In `apps/patients/templatetags/patient_tags.py`, remove the tuple
   `(Patient.Status.EMERGENCY, 'Emergência', 'exclamation-triangle', 'btn-danger')`
   from the `status_transitions` list inside `available_status_actions`.
3. In the same file, remove the now-dead mapping entry
   `Patient.Status.EMERGENCY: 'emergency_admission'` from `_get_action_name`.
4. In `apps/patients/templates/patients/partials/admission_section.html`,
   delete the entire `<!-- Emergency Admission Modal -->` block: the
   `<div class="modal fade" id="emergency_admissionModal" ...>` element and
   its contents (roughly lines 289-336).
5. In `test_action_labels_are_meaningful`, remove the unused
   `Patient.Status.EMERGENCY: "Emergência"` entry from `expected_labels`.
6. Run the verification commands; confirm template tag tests pass (green) AND
   the untouched backend tests of emergency admission still pass.

Refactor steps:

- None beyond the dead-code removals listed above; keep the rest of
  `available_status_actions` and the partial untouched.

Verification commands:

- `./scripts/test.sh apps.patients.tests.test_status_template_tags`
- `./scripts/test.sh apps.patients.tests.test_status_changes apps.patients.tests.test_forms`

Definition of done:

- Emergency action absent from `available_status_actions` output for every
  current status (tag skips current status anyway; no EMERGENCY tuple left).
- No `emergency_admissionModal` markup left in the partial.
- `git diff --stat` shows only the three files listed above.
- Backend emergency tests pass unmodified.
