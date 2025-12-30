# EquipeMed LLM-Friendly Django Requirements

Updated: February 2026  
Maintainer: Solo developer collaborating with CLI-based coding assistants (Claude Code, Codex CLI, Gemini CLI, Amp CLI)

This document is the authoritative set of requirements for EquipeMed’s architecture, collaboration practices, and future AI work. It replaces all previous project-level requirement drafts.

---

## 1. Project Overview

- **Purpose:** Support doctors with patient tracking, daily notes, PDF forms, and report generation.
- **Team Model:** Single maintainer using multiple CLI-based LLM assistants for coding and reviews.
- **Planned Growth:** Add AI-assisted summarisation, clinician draft generation, and a Matrix bot for residents while keeping clinicians firmly in control.

---

## 2. Right-Sized Architecture

### 2.1 App Layout

- Maintain Django’s app-per-domain structure (`patients`, `events`, `pdf_forms`, etc.).
- Each app keeps core modules (`models.py`, `views.py`, `urls.py`, `tests/`, optional `forms.py`, `admin.py`, `signals.py`).
- Create `services.py` in an app when a workflow spans multiple models or exceeds ~30 lines. Keep the module even if it starts small so assistants know where to place logic.
- Only add `tasks.py` when asynchronous work is required for that app.
- Avoid generic “core business logic” directories, deep inheritance chains, or hexagonal/clean architecture structures. Domain code lives beside the models it manipulates.

### 2.2 Models

- Remain explicit and auditable: define fields, validators, lifecycle flags, and `created_at/updated_at` plus user attribution.
- Simple state toggles or validation can live on the model.
- When logic orchestrates multiple updates (admissions, discharges, record-number history), move it to services to keep models readable for humans and LLMs.

### 2.3 Services

- Location: `apps/<app>/services.py`.
- Style: plain functions, keyword-only parameters, type hints, descriptive docstrings explaining inputs, side-effects, and return values.
- Scope: implement single business actions (e.g., `admit_patient`, `generate_daily_note_pdf`, `update_tag_assignments`).
- Services may call other services but should avoid hidden state or class-based singletons.

### 2.4 Views & API Endpoints

- Views validate input, enforce permissions, call exactly one service, and assemble the response.
- Direct ORM reads are acceptable for simple list/detail operations. Complex filtering or writes go through services.
- Include concise comments when permissions or workflow steps are non-obvious so assistants don’t miss critical guards.

### 2.5 Forms, Reports, PDFs

- Keep PDF/form generation isolated in dedicated apps (`pdf_forms`, `reports`) with templates version-controlled in Git.
- Provide service entry points for generation logic so updates are consistent across web views, APIs, and future bots.

---

## 3. Collaboration With LLM Assistants

### 3.1 Specs & Change Notes

- Use short design briefs in `prompts/` for anything beyond trivial fixes. Capture scope, impacted files, acceptance criteria, and test expectations.
- Skip heavy proposal tooling unless the change is risky or cross-cutting.

### 3.2 Assistant Brief Template

- Maintain a reusable checklist (context, target modules, constraints, known pitfalls) to paste into Codex, Claude, Gemini, or Amp. Update it whenever architecture patterns shift.

### 3.3 Shared Knowledge

- Keep `CLAUDE.md` current with commands and caveats; add similar guides for other assistants if helpful.
- Log important decisions via commit messages or small markdown notes to keep everyone aligned without sprawling specs.

### 3.4 Commit & Review Hygiene

- Divide work into focused commits with clear intent.
- Run targeted tests (or clearly note if they’re skipped) before handing changes to an assistant or reviewer.

---

## 4. Future AI & Automation Features

### 4.1 LLM App Skeleton

Create `apps/llm/` before enabling AI features:

```
apps/llm/
├── __init__.py
├── clients.py        # Provider adapters (OpenAI, Claude, etc.)
├── schemas.py        # Pydantic/dataclass payloads
├── prompts.py        # Versioned prompt constants
├── tasks.py          # Celery/Django-RQ jobs
├── stores.py         # Persistence helpers for AI outputs
└── exceptions.py     # Custom error types
```

### 4.2 Prompt Management

- Store live prompts in `prompts.py` modules with explicit version numbers (`DISCHARGE_SUMMARY_PROMPT_V1`).
- Explain major changes in comments/docstrings so diffs carry intent.
- Keep exploratory prompt drafts in markdown, but only executed prompts belong in code.

### 4.3 Execution Model

- Start synchronous behind feature flags if latency is acceptable, but plan for asynchronous execution via Celery or Django-RQ when:
  - End-to-end calls exceed acceptable response times.
  - Rate limits/quotas need centralized throttling and retries.
  - Workflows require auditing or human approval steps.
- Flow: View → Service → Task enqueue → LLM call → Persist result → Notify clinician.

### 4.4 Persistence & Safety

- Store AI outputs separately from clinician-authored data.
- Capture metadata: prompt version, provider/model id, token usage (if available), timestamp, requesting user, review/approval state.
- Build UI/admin flows so clinicians approve or edit AI drafts before publication; log every approval or modification for auditing.
- Never overwrite original medical notes—AI content augments, it doesn’t replace.

### 4.5 Provider Flexibility

- Drive provider selection via Django settings; inject provider clients into services so swapping APIs is configuration-only.

### 4.6 Matrix Bot Guidance

- Treat the Matrix bot as another client of the service layer; it should reuse existing workflows.
- Enforce permissions and rate limiting in services, not in the bot adapter, to keep rules centralized.

---

## 5. Testing & Quality Assurance

- Continue using pytest with descriptive test names (`test_admit_patient_already_admitted_raises_error`).
- Add service-level unit tests whenever logic moves out of models/views.
- Ensure each service test covers success, failure, and edge cases (permissions, validation).
- Snapshot or fixture-test prompts when wording or structure changes to prevent regressions.
- Maintain integration tests for critical workflows (admissions, discharges, PDF exports) so refactors remain safe.

---

## 6. Operational Process

- **Monthly Architecture Cleanup:** Schedule a short session to move new logic into services, prune dead code, and confirm tests/lint pass. Keeps the repo assistant-friendly.
- **Documentation Resync:** Update README snippets, `CLAUDE.md`, and assistant briefs whenever commands, services, or prompts evolve.
- **Feature Flags:** Wrap experimental features—especially AI—in Django settings or waffle flags for safe rollout and quick rollbacks.
- **Backups & Auditing:** Maintain reliable database backups and ensure audit/history tables remain intact after migrations.
- **Security:** Guard API keys and PHI. Store secrets in `.env`, avoid logging sensitive data, and apply least-privilege principles at the service layer.

---

## 7. Quick Reference Checklist

1. Review task context and impacted apps.
2. Keep models explicit; move multi-step workflows into `services.py`.
3. Write or update service tests before/after refactors.
4. Keep views thin: validate → permission → service → respond.
5. Version executable prompts in code, snapshot when they change.
6. Persist AI outputs with metadata; enforce human approval.
7. Document noteworthy decisions in commits or short briefs.

---

Follow this document to keep EquipeMed maintainable for a solo developer and predictable for every LLM assistant that contributes work. Any new architectural or AI-related decisions should be reflected here.\*\*\*
