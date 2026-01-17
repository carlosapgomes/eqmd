## Why

Clinicians need a fast, chat-based workflow to query inpatient demographics via Matrix without logging into the full EquipeMed UI.

## What Changes

- Add a Matrix bot that handles `/buscar` patient search and demographic lookup in a DM room.
- Add bot conversation state, message handling, and audit logging for chat activity.
- Enforce existing EQMD patient access permissions in bot search/results.
- Add admin tools to (re)provision bot DM rooms and auto-verify Matrix user bindings.
- Add a management command to run the bot within the Django project.

## Impact

- Affected specs: `matrix-bot`
- Affected code: `apps/matrix_integration/`, `apps/botauth/`, `apps/patients/`, user admin actions
