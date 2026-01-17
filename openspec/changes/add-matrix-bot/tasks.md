## 1. Tests (Red First)

- [x] 1.1 Unit tests for search ranking and query parsing.
- [x] 1.2 Bot conversation flow tests (search → selection → demographics).
- [x] 1.3 Permission enforcement tests for search filtering and detail access.
- [x] 1.4 Input validation tests for oversized and unsupported commands.
- [x] 1.5 State timeout tests for pending selections.
- [x] 1.6 Audit log write tests.
- [x] 1.7 Admin provisioning action tests.

## 2. Implementation

- [x] 2.1 Add bot runtime module under `apps/matrix_integration/bot/` using `matrix-nio` and a simple state machine.
- [x] 2.2 Add a conversation state model to store pending search results per DM room.
- [x] 2.3 Implement patient search service (inpatients + emergency) with ranked results and limit to 5.
- [x] 2.4 Implement `/buscar` command parsing with optional prefixes (`reg:`, `leito:`, `enf:`).
- [x] 2.5 Add numeric selection flow and demographic response formatting (Portuguese).
- [x] 2.6 Enforce permission checks using existing permission helpers for search visibility and patient access.
- [x] 2.7 Add JSONL audit logging to `logs/matrix_bot_audit.log` for inbound/outbound messages.
- [x] 2.8 Configure audit log rotation (daily, keep 60 days).
- [x] 2.9 Add management command `run_matrix_bot` to start the bot process.
- [x] 2.10 Add Django admin action on user list to (re)provision DM rooms and auto-verify Matrix bindings.
- [x] 2.11 Extend/adjust provisioning command to reuse existing DM rooms and support re-provisioning.
