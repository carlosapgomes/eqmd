## Context

EquipeMed already provisions Matrix users and DM rooms. The bot must run inside the Django project, use existing models, and support a simple patient search flow in Portuguese, with audit logging.

## Goals / Non-Goals

- Goals:
  - Provide a `/buscar` command in a 1:1 DM room that returns inpatient demographics.
  - Keep interaction simple (numbered selection) while leaving room for future LLM workflows.
  - Avoid new services or queues; run as a Django management command.
- Non-Goals:
  - LLM drafting features (future phase).
  - UI changes in Matrix clients.
  - Rate limiting (deferred).

## Decisions

- **Matrix library**: Use `matrix-nio` for async client support and compatibility with Synapse.
- **Conversation framework**: Implement a small custom state machine stored in the database (no LangGraph/LangChain for MVP).
- **User identity**: Auto-create and auto-verify `MatrixUserBinding` during admin provisioning; map Matrix users to EQMD users without extra user UI steps.
- **Room policy**: Bot only responds in the provisioned DM room. Messages elsewhere receive a Portuguese redirect prompt.
- **Search approach**: Use Django ORM queries across `Patient` + active `PatientAdmission` with weighted ranking; limit to 5 results.
- **Authorization**: Use existing permission helpers (`can_view_patients`, `can_see_patient_in_search`, `can_access_patient`) so bot behavior matches current role restrictions.
- **Audit logging**: Write JSONL entries to `logs/matrix_bot_audit.log` with daily rotation and 60-day retention.

## Permission Mapping

- Search availability: `can_view_patients(user)`
- Search visibility: `can_see_patient_in_search(user, patient)`
- Patient details: `can_access_patient(user, patient)`

## Ranking (MVP)

Score matches by strongest identifiers first. Use combined filters to narrow results, then sort by score desc, fallback to most recent admission datetime.

Proposed scoring (MVP):

- Record number exact: +1000, partial: +500
- Bed exact: +800, partial: +400
- Ward exact (name or abbreviation): +600, partial: +300
- Name token match: +200 per token
- Recency boost: +max(0, 50 - days_since_admission)

## Error Handling (MVP)

- Matrix disconnect: retry with exponential backoff (3 attempts) before giving a generic error to the user.
- Database errors/timeouts: reply "Sistema temporariamente indisponivel. Tente novamente."
- No results: reply "Nenhum paciente encontrado."
- Invalid selection: reply "Selecao invalida. Responda com o numero da lista."

## Input Validation

- Max command length: 200 characters.
- Prefix values: 50 characters each; ignore values beyond limit.
- Unrecognized command: reply with a short help prompt for `/buscar`.

## State Management

- One active search per DM room; a new `/buscar` cancels the previous pending selection.
- Pending selection expires after 5 minutes of inactivity.
- On bot restart, pending states are cleared.

## Audit Log Schema

Each JSONL entry includes:

- `timestamp` (ISO8601)
- `direction` (`inbound` or `outbound`)
- `user_id` (EQMD user id)
- `matrix_user` (Matrix user id)
- `room_id`
- `action` (e.g., `patient_search`, `patient_select`, `error`)
- `message` (raw text)
- `results_count` (optional)
- `selected_patient_id` (optional)

## Risks / Trade-offs

- Persisting conversation state in DB adds schema changes but avoids losing context on restarts.
- Auto-verifying bindings reduces user friction but relies on admin accuracy.

## Migration Plan

- Add new bot models and management command.
- Deploy with bot process off by default; enable after provisioning bot token.

## Open Questions

- None.
