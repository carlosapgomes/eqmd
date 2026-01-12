# Phase 01 – Baseline Assessment Prompt

You are implementing Phase 01: Baseline Assessment & Safety Freeze.

## Instructions
Follow docs/01-baseline-assessment.md exactly.

## Your Tasks
1. Create feature branch: `feature/oidc-delegated-bots`
2. Audit current authentication (document in markdown)
3. Inventory ALL API endpoints with bot access recommendations
4. Identify forbidden endpoints (bots must never access)
5. Document decorator behavior for bots
6. Run existing tests to establish baseline

## Critical Rules
- DO NOT modify any code in this phase
- ONLY create documentation files in `docs/security/`
- Be THOROUGH - missing an endpoint is a security risk
- When in doubt about bot access, recommend DENY

## Output
Create these files:
- `docs/security/current-auth-audit.md`
- `docs/security/endpoint-inventory.md`
- `docs/security/bot-forbidden-endpoints.md`
- `docs/security/decorator-bot-behavior.md`
- `docs/security/baseline-test-results.md`

## Verification
```bash
git branch --show-current  # Should show feature/oidc-delegated-bots
git diff main --stat       # Should show only new docs
uv run pytest apps/core/tests/test_permissions/ -v  # Must pass
```
