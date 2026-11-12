# Slice 01 Prompt: hide-emergency-status-action

Execute ONLY Slice 01 as described in `slice-01.md`.

Read in this exact order before changing code:

1. `/projects/dev/eqmd/AGENTS.md`
2. `/projects/dev/eqmd/openspec/changes/hide-emergency-status-action/proposal.md`
3. `/projects/dev/eqmd/openspec/changes/hide-emergency-status-action/design.md`
4. `/projects/dev/eqmd/openspec/changes/hide-emergency-status-action/specs/patient-status-actions/spec.md`
5. `/projects/dev/eqmd/openspec/changes/hide-emergency-status-action/slices/slice-01.md`
6. `/projects/dev/eqmd/openspec/changes/hide-emergency-status-action/slices/slice-01-prompt.md`

Rules:

- Follow TDD strictly (tests first, red -> green -> refactor).
- Only touch these files:
  - `apps/patients/templatetags/patient_tags.py`
  - `apps/patients/templates/patients/partials/admission_section.html`
  - `apps/patients/tests/test_status_template_tags.py`
- Hide the emergency action by REMOVING the EMERGENCY tuple from
  `status_transitions` in `available_status_actions` (single generation
  point). Do NOT use CSS or template conditionals.
- Remove the orphaned `emergency_admissionModal` block from
  `admission_section.html`.
- Remove the dead `EMERGENCY` entries from `_get_action_name` and from the
  `expected_labels` map in the label test.
- Do NOT modify `EmergencyAdmissionView`, `EmergencyAdmissionForm`, the URL
  `emergency_admission`, signals, permissions, or their tests. Those tests
  (`test_status_changes.py`, `test_forms.py`) must pass WITHOUT changes —
  that is the proof the backend stayed intact.
- Do NOT touch the patient list status filter, the status badge, the
  "Paciente em Emergência" alert, or the "Tipo de Internação" emergency
  option in the admit modal.
- Run both verification commands listed in the slice.
- Stop after this slice is green. There is no Slice 02.

Checklist:

Spec

- [ ] requirements understood

Tests (RED)

- [ ] `test_available_status_actions_outpatient` updated to assert EMERGENCY absent
- [ ] `test_available_status_actions_inpatient` updated to assert EMERGENCY absent
- [ ] tests fail before implementation (red)

Implementation (GREEN)

- [ ] EMERGENCY tuple removed from `status_transitions`
- [ ] dead EMERGENCY entry removed from `_get_action_name`
- [ ] `emergency_admissionModal` block removed from the partial
- [ ] dead EMERGENCY entry removed from `expected_labels` in the label test
- [ ] template tag tests pass

Backend intact

- [ ] `./scripts/test.sh apps.patients.tests.test_status_changes` passes unmodified
- [ ] `./scripts/test.sh apps.patients.tests.test_forms` passes unmodified
- [ ] `git diff --stat` limited to the three allowed files

Refactor (CLEAN)

- [ ] no leftover dead code from the removal

Final

- [ ] all checklist boxes in this prompt marked
- [ ] stop here; this change has a single slice
