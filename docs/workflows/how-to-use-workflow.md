# How to Use the Two‑LLM Workflow

Use this when working with two agents:
- **Planner/Debugger (Codex)** → planning, slicing, troubleshooting
- **Implementer (glm‑4.7 / pi)** → small, scoped implementation only

---

## 1) Planning (non‑trivial changes)

Prompt Codex with:
```
Use the two‑LLM workflow in docs/workflows/llm-collab.md.
Create/continue the OpenSpec change for <feature>.
Produce slice plan + slice prompts (glm).
Stop after the artifacts are written.
```

Example:
```
Use the two‑LLM workflow in docs/workflows/llm-collab.md.
Create/continue the OpenSpec change for "add reports app".
Produce slice plan + slice prompts (glm).
Stop after the artifacts are written.
```

---

## 2) Small changes (skip OpenSpec)

Prompt Codex with:
```
Use the two‑LLM workflow, but skip OpenSpec (trivial change).
Create a 1–2 slice plan and slice prompts.
```

---

## 3) After GLM runs a slice (debug help)

Prompt Codex with:
```
Use the two‑LLM workflow.
I ran slice-XX and got this error:
<paste logs>
Analyze and propose the smallest fix. Do not implement.
```

---

## 4) Generate GLM prompts (if missing)

Prompt Codex with:
```
Generate GLM prompts using docs/workflows/slice-prompt-template.md
for slices 01–NN under openspec/changes/<change>/slices.
```

---

## 5) Sync + Archive (end of change)

Prompt Codex with:
```
Use OpenSpec to sync specs and archive change <name>.
```
