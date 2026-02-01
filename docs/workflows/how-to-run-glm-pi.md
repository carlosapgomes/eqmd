# How to Run GLM/pi (One‑Page)

This assumes you are using the pi coding agent with glm‑4.7.

---

## Before Each Slice

1) Start with empty context.
2) Provide the slice prompt file:
   - `openspec/changes/<change>/slices/slice-XX-glm-prompt.md`
3) Ensure the model reads required files in order.

---

## What to Send to GLM/pi

Paste the entire contents of:
```
openspec/changes/<change>/slices/slice-XX-glm-prompt.md
```

---

## Expected GLM/pi Behavior

- Read AGENTS.md, spec/design, then the slice files.
- Implement only the current slice.
- Follow TDD and run the verification command.
- Mark checklist boxes in the slice prompt before stopping.

---

## If GLM/pi Drifts Out of Scope

- Stop it immediately.
- Re‑send the slice prompt and add:
  “Only implement what slice‑XX.md includes. Do not touch other files.”

---

## After Each Slice

- Save output (files changed, tests run, results).
- If tests fail, send logs to the Planner/Debugger LLM.

---

## Guardrails Reminder

- Never run destructive commands unless explicitly approved.
- No database drops/resets without explicit user approval.
- No package installs outside the app container.

