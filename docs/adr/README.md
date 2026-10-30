# Architecture Decision Records

Registros de decisões arquiteturais importantes do projeto.

## ADRs ativas

- [ADR-0001 — Deterministic Development Quality Gates][adr-0001]
  — _Accepted (2026-08-29)_
- [ADR-0002 — Deploy application-level duplicate prevention with
  deferred database constraint][adr-0002]
  — _Accepted (2026-08-30)_
- [ADR-0003 — Manter cadastros duplicados separados, sem merge
  clínico][adr-0003]
  — _Accepted (2026-09-01)_

## ADRs propostas

- [ADR-0004 — Correção delimitada de segurança da imagem produtiva][adr-0004]
  — _Proposed (2026-10-29)_

[adr-0004]: ADR-0004-bounded-production-image-security-remediation.md
[adr-0001]: ADR-0001-deterministic-development-quality-gates.md
[adr-0002]: ADR-0002-deploy-application-level-duplicate-prevention-with-deferred-database-constraint.md
[adr-0003]: ADR-0003-keep-duplicate-patients-separate-no-merge-tooling.md

## Como criar nova ADR

1. Execute `python3 adr_generator.py --title "Sua decisão"`.
2. Revise contexto, decisão, alternativas e consequências.
3. Commit da ADR junto do change relacionado.
