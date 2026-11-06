---
name: verify-eqmd
description: "Drive the real EquipeMed web app (Django, pt-BR clinical UI) in
  Chrome and prove UI/UX behaviour end to end: student draft supervision,
  timeline draft badges and filters, doctor approval, discharge/APAC/photo
  drafts. Use when a change touches views, templates, permissions, or event
  flows and you need browser evidence from the live dev stack."
---

# verify-eqmd

Scripted browser verification for this repository. It drives the **running**
development stack the way a clinician does — login form, patient timeline,
dropdown menus, EasyMDE editor, FilePond uploads — and captures screenshots,
Playwright traces, database row state, and a command log for every run.

Use it when a change touches templates, views, permission gates, or event
workflows and you want proof from the live app instead of unit tests. The
mapped journeys cover the student draft supervision rollout
(`openspec/changes/add-student-draft-supervision`).

Everything runs from `.pi/skills/verify-eqmd/harness/`. The commands below are
the only supported entry points; each section states what the step does and
what it refuses to do.

## Launch

**This skill never starts, stops, or restarts the app.** The dev stack is
shared with the operator's manual testing, so "launch" means: adopt the stack
that is already running and confirm it is usable.

The running stack in this environment:

- `eqmd_dev` — Django `runserver 0.0.0.0:8000` inside the container, published
  to the host as `http://127.0.0.1:8779`.
- `eqmd_postgres` — PostgreSQL 15, reachable from `eqmd_dev`.

Readiness is: the login page answers `200` with the title
`Login - EquipeMed`, and the runserver process belongs to whoever started the
container (you are a guest). Then scaffold the disposable data:

```bash
cd .pi/skills/verify-eqmd/harness
npm install        # once: pins playwright 1.65.0, NO browser download
npm run doctor     # read-only readiness gate (see below)
npm run setup      # creates the disposable users/patient for this run
```

`npm run setup` runs `scaffold.py` inside the container through
`docker exec -i eqmd_dev python manage.py shell`, which it feeds on stdin. It
creates, and is idempotent for:

- `verify.student@eqmd-verify.invalid` — `profession_type=4`, group
  `Students`, `password_change_required=False`, `terms_accepted=True`, allauth
  `EmailAddress(verified=True)`; e-mail verification is mandatory here, so
  without the verified address the login redirects to the verification page.
  The password comes from `EQMD_VERIFY_PASSWORD` (`Verify!2026#eqmd`).
- `verify.doctor@eqmd-verify.invalid` — `profession_type=0`, group
  `Medical Doctors`, same login readiness.
- one patient named `VERIFICACAO Skill <run-id>`, owned by the doctor account,
  created empty so each journey starts from zero timeline events. `scaffold.py`
  never reuses a patient: if a row with that exact name already exists it
  creates nothing, exits non-zero and names the row, because an equal name does
  not prove this run created it. The `id`, `created_by` and `created_at` of the
  row it did create go into `scaffold.json` as the run's ownership certificate —
  the only thing cleanup may delete.

Migrations: this skill applies none. `doctor` runs `manage.py migrate --check`
(read-only); unapplied migrations fail the doctor and the journeys must not
run — migrating a shared dev database is the operator's call, not a
verification step.

Run id and evidence location come from the environment:

- `EQMD_VERIFY_RUN_ID` (default `YYYYMMDD-HHMMSS`) — names the evidence
  directory and the scaffold patient.
- `EQMD_VERIFY_PATIENT_NAME` (default `VERIFICACAO Skill <run-id>`) — the one
  patient `setup` creates and the only patient `cleanup` deletes.
- `EQMD_VERIFY_PATIENT_ID` / `EQMD_VERIFY_PATIENT_CREATED_BY` (default: the
  values this run's `scaffold.json` recorded) — the ownership certificate
  `cleanup` deletes by. Set them only for a recovery run whose `scaffold.json`
  is gone; `cleanup` re-verifies id, name and creator before deleting.
- `EQMD_VERIFY_BASE_URL` (default `http://127.0.0.1:8779`) — published port.
- `EQMD_VERIFY_CONTAINER` (default `eqmd_dev`) — container owning the server.
- `EQMD_VERIFY_EVIDENCE_ROOT` (default `/tmp/eqmd-verify`) — evidence root.

## Doctor

One read-only check that answers "is this instance worth driving?":

```bash
cd .pi/skills/verify-eqmd/harness && npm run doctor
```

It writes `doctor.json` into the run's evidence directory and exits `1` if any
check fails. It is read-only including its one probe `POST`: Django's CSRF
middleware rejects that request before the login view runs, so it creates no
session and writes no row.

1. `docker inspect eqmd_dev` reports `running` (Docker CLI only; never
   `docker start`).
2. `GET /accounts/login/` returns `200` with
   `<title>Login - EquipeMed</title>`.
3. The login form carries a `csrfmiddlewaretoken`, **and** a `POST
   /accounts/login/` carrying the login fields but no token and no cookies is
   rejected with `403` (`CSRF cookie not set`) while setting no `sessionid`
   cookie. That is a token-presence plus CSRF-gate check, nothing more:
   doctor does not test whether credentials are valid. Valid credentials,
   successful login and the redirect to `/dashboard/` are proven by the
   journeys, which log in through the real form with the scaffold accounts.
4. The served checkout is identified: the doctor runs `git rev-parse` inside
   the container at `/app` and records the branch and short hash.
5. The served code still contains the draft-review surface: the doctor greps
   the container's `event_card_base.html` for the draft badge text
   (`Rascunho · há`) and fails when the match count is zero.
6. `connection.ensure_connection()` succeeds inside the container.
7. `manage.py migrate --check` reports no unapplied migrations.

**Read the served-checkout line before trusting a green run.** `eqmd_dev`
mounts `/projects/dev/eqmd` at `/app` (observed: `main@94db260`), which is not
necessarily the worktree you are editing. A journey proves the code the
container serves. If the hashes differ, the evidence describes the other
checkout.

## Drive

Node + Playwright driving **system Chrome** through `channel: "chrome"`
(`/usr/bin/google-chrome`, 155.x). No browser binary is downloaded and no
project dependency is touched: `playwright` 1.65.0 lives in
`harness/node_modules`, which `harness/.gitignore` keeps out of git. Every
Python step runs inside `eqmd_dev` via `docker exec`; nothing is installed on
the host or in the project environment.

Run one journey end to end (doctor, setup, journey, cleanup — cleanup always
runs, including after a failure):

```bash
cd .pi/skills/verify-eqmd/harness
npm run verify -- --journeys j3        # one journey, the recommended proof
npm run verify -- --journeys j1,j4     # several, fresh scaffold rows each
npm run verify -- --all                # every mapped journey
```

Individual helpers, when you need to hold state between steps:

```bash
npm run doctor
npm run setup
npm run journey:j3      # j1..j6
npm run cleanup
```

Real controls used by the journeys, verified against the running app:

- Login: `#id_login` (e-mail field), `#id_password`,
  `button[type=submit]`; success redirects to `/dashboard/`.
- Timeline: `/patients/<patient-uuid>/timeline/`.
- Create menu: `#createEventDropdownDesktop`, then the item under
  `ul[aria-labelledby="createEventDropdownDesktop"]`. The same links exist in a
  hidden mobile menu — always scope to the desktop `<ul>`, or Playwright waits
  forever on an invisible element.
- Note editor: EasyMDE replaces `#id_content` with CodeMirror; click
  `.CodeMirror`, then type with the keyboard (the textarea is not fillable).
- Draft badge: `.draft-badge` inside `article.timeline-card` (text
  `Rascunho · há …`), tint class `timeline-card-draft`.
- Review link: `a[aria-label="Revisar rascunho da nota"]` →
  `/simplenotes/<uuid>/update/`.
- Supervision banner: `[data-draft-supervision-banner]`.
- Approval button: `button[name="save_final"]` (doctors/residents only).
- Drafts filter: `?drafts_only=1`, checkbox `#oc-drafts_only` (desktop
  offcanvas prefix `oc-`).
- Discharge draft: `button[name="save_draft"]`, `button[name="save_final"]`,
  delete confirmation `#confirmDelete` + `#deleteBtn`.
- Photo upload: `input[name="filepond"]` via `setInputFiles`, then poll the
  hidden `input[name="upload_id"]` for the FilePond server id.
- APAC capture: `.procedure-search-input` and `.icd10-search-input`, suggestion
  items in `.procedure-results` and `#icd10-results-main` (`.dropdown-item`),
  `textarea[name="main_diagnosis"]`.

Journeys open **one browser context per role** (`j.open('student', …)`,
`j.open('doctor', …)`), so "student then doctor on the same draft" is two real
sessions with separate cookie jars, the way two people would act.

Mapped journeys live in `features/`; each file names the selectors and the
observable end state:

- `features/01-student-draft-create.md` — new note becomes a draft (J1)
- `features/02-drafts-only-filter.md` — drafts-only filter and role-dependent
  actions (J2)
- `features/03-doctor-finalizes-draft.md` — `Salvar definitivo`, author kept,
  approver recorded (J3)
- `features/04-discharge-report-draft.md` — a student cannot finalize a
  discharge report (J4)
- `features/05-photo-draft.md` — FilePond photo draft: inline view, download
  denied, hard delete (J5)
- `features/06-apac-update.md` — APAC update view prefilled from the persisted
  submission (J6)

## Evidence

Every run writes to `/tmp/eqmd-verify/<run-id>/`. The location is ephemeral by
design; copy it elsewhere if it has to outlive the session.

- `command-log.jsonl` — every `docker`/`docker exec` call a helper made,
  with exit code, duration and the tail of its output.
- `doctor.json` — readiness checks and the served checkout.
- `scaffold.json` — created users/patient ids, the patient's ownership
  certificate (`id`, `created_by`, `created_at`) and its permission probe.
- `summary.json` — orchestrator record of which helper ran, with exit codes.
- `cleanup.json` — rows removed, accounts deactivated, the ownership basis
  used (`recorded-id` or `name-fallback`), and `refused` plus `reason` when
  ownership could not be proven.
- `cleanup-evidence-check.json` — proof the evidence directory survived
  cleanup.
- `db/<label>.json` — read-only ORM probe (row state) per checkpoint.
- `<journey>/report.json` — steps, assertions, console errors, native dialogs.
- `<journey>/screenshots/*.png` — the screen at each checkpoint.
- `<journey>/traces/<role>.zip` — Playwright trace; open with
  `npx playwright show-trace <file>`.
- `fixtures/verify-photo.png` — generated FilePond upload fixture, kept out of
  the repository.

Proof standards this skill holds itself to:

- Drive the real user path: real login form, real dropdown, real editor
  typing, real buttons. No test-only endpoints, no internal setters.
- Capture the action and the resulting state for every checkpoint
  (screenshot plus a text assertion).
- Verify side effects next to the visuals: `db/<label>.json` reads rows with
  the ORM (`is_draft`, `created_by`, `draft_promoted_by`), and the photo
  journey compares the stored file path before and after deletion.
- A failed assertion fails the journey with its message in
  `<journey>/report.json`. Nothing is relaxed to make a journey green.

Read a result with:

```bash
jq -r '.status, (.steps[] | "\(.status)\t\(.name)")' \
  /tmp/eqmd-verify/<run-id>/<journey>/report.json
```

## Cleanup

```bash
cd .pi/skills/verify-eqmd/harness && npm run cleanup
```

`cleanup.py` (inside the container) removes only what `scaffold.py` created for
**this run**:

- the one patient this run scaffolded, selected by the id recorded in
  `scaffold.json` (`EQMD_VERIFY_PATIENT_ID`) and re-verified before deletion:
  same id, same run name, and `created_by` is this run's scaffold account. Only
  that verified id's events are hard-deleted (`Event.patient` is
  `on_delete=PROTECT`, and never-finalized drafts are hard-deleted rows by
  design). A row that is already gone is reported `already_clean` and cleanup
  still succeeds;
- deactivates the two `@eqmd-verify.invalid` accounts, strips their passwords,
  and reports `password_still_valid` so the run can prove they cannot log in
  again. Those two accounts are fixed e-mail singletons that every run reuses
  (`scaffold.py` is idempotent on the e-mail), so cleanup always covers exactly
  them and re-activates them on the next `setup`.

The patient scope is a run's own row, never a `VERIFICACAO Skill` prefix sweep:
a cleanup under run id B leaves run id A's patient and its events untouched, so
two runs can share the stack. Ownership — not the name — decides what is
deleted. When no certificate is available (a recovery run whose `scaffold.json`
is gone), cleanup falls back to an exact name match and accepts it only if
exactly one row carries the run's name **and** a verify account created it;
that fallback is same-namespace only, so any row named
`VERIFICACAO Skill <run-id>` that a verify account created is deletable by that
run id. Everything else is refused with a non-zero exit and nothing deleted: an
id/name/creator mismatch, or more than one row with the run's name
(`refused: true` plus `reason` in `cleanup.json`).

Rows from an older run are therefore *not* swept by a newer one — to clear a
failed attempt or a stale leftover, run cleanup under the id that created it:

```bash
EQMD_VERIFY_RUN_ID=<old-run-id> npm run cleanup
# certificate gone? name the row explicitly instead:
EQMD_VERIFY_RUN_ID=<old-run-id> EQMD_VERIFY_PATIENT_ID=<patient-uuid> npm run cleanup
```

`run.mjs` invokes cleanup after every journey and once more at the end; both
invocations use the run's own certificate, so the final call is an idempotent
no-op for this run rather than a sweep of anything else. If `setup` refuses to
scaffold, `run.mjs` stops the remaining journeys (nothing was created to drive)
and only that final cleanup still runs; because the refused run has no
certificate, that final cleanup uses the name rule and can therefore clear one
same-namespace stale row carrying this run's exact name — never a row another
run id owns. `cleanup.json` reports
`run_patient_remaining` (must be `0` for the run to pass),
`verify_patients_outside_scope` (a read-only count of other `VERIFICACAO Skill
…` patients this cleanup deliberately left alone) and the `ownership` basis it
used.

It never deletes evidence, never truncates tables, never touches a patient or
user outside its scope, and never kills a process (the skill starts none). Run
it after every iteration, including failed ones, so a broken attempt leaves no
scaffold rows behind.

## Helpers

Every script is executable with the invocation shown:

- `scaffold.py` — `npm run setup` (not run directly): creates the users and
  patient inside the container and prints `EQMD_VERIFY_SCAFFOLD=<json>`. Refuses
  (non-zero exit, nothing created) when the run's patient name is already taken,
  and reports the new row's ownership certificate.
- `cleanup.py` — `npm run cleanup`: deletes the patient this run scaffolded,
  verified by the recorded id/name/creator, plus its events; deactivates the two
  accounts; prints `EQMD_VERIFY_CLEANUP=<json>`.
- `probe.py` — invoked by journeys through `lib/probe.mjs`: read-only ORM dump
  of the patient's events/photos plus an optional file-existence check.
- `doctor.mjs` — `npm run doctor`: readiness gate, writes `doctor.json`.
- `setup.mjs` — `npm run setup`: checks the harness install, runs
  `scaffold.py`, writes `scaffold.json`.
- `cleanup.mjs` — `npm run cleanup`: runs `cleanup.py`, writes `cleanup.json`
  and the evidence-survival check.
- `run.mjs` — `npm run verify -- --journeys j3`: doctor, setup, journey(s),
  cleanup (cleanup always last).
- `journey-j1-draft-create.mjs` … `journey-j6-apac-update.mjs` —
  `npm run journey:j1` … `npm run journey:j6`: one journey each, with report,
  screenshots and trace.
- `lib/config.mjs` — paths, URLs, run id, credentials, patient name and
  ownership certificate.
- `lib/evidence.mjs` — evidence paths, JSON writes, command log.
- `lib/docker.mjs` — `docker exec` / Docker CLI wrapper that logs every call.
- `lib/harness.mjs` — browser and context lifecycle, steps, assertions,
  report.
- `lib/probe.mjs` — runs `probe.py` for one checkpoint.
- `lib/actions.mjs` — shared user-path actions (timeline, create, editor,
  save).
