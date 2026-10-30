# S2 — Dependências HTTP e confiança TLS

## Identity

- Change: `harden-production-image-security`.
- Slice: `eqmd-sec-002`; tasks 2.1–2.3 de `../tasks.md`.
- Pré-condição: S1b aceito e S2 explicitamente autorizado; não iniciado.

## Objective

Executar Django/DRF/certifi corrigidos em runtime lock-backed e comprovar
login, autorização, CSRF e HTTP/OIDC sem alterar contratos ou schema.

## Read first

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- `../proposal.md`, `../design.md`, decisões D1/D3/D4/D6.
- `../specs/production-image-security/spec.md`, `../evidence/baseline.json`.
- ADR-0001/ADR-0004, relatórios aceitos S1a/S1b, `pyproject.toml`, `uv.lock`
  e `config/third_party_apps.py`.
- `config/settings.py`, `apps/botauth/authentication.py`, `apps/botauth/tokens.py`.
- `apps/botauth/tests/test_authentication.py`, `test_bot_api.py` e
  `test_delegation.py` no mesmo diretório.
- Convenções de fixtures em `apps/accounts/tests/helpers.py` e testes core.

## Requirements

- R1: Django `>=5.2.17,<5.3`, DRF `>=3.18.2,<3.19`, certifi `>=2026.10.18`
  declarados e resolvidos seletivamente, sem atualizar Pillow ainda.
- R2: versões reais dos três alvos correspondem exatamente às versões do lock;
  testes executam no ambiente reconstruído, sem package install ad hoc.
- R3: rotas e respostas legítimas, negação de acesso, CSRF e OIDC continuam
  corretas com fixtures sintéticas; check de drift não gera migration.
- R4: alterações transitivas têm causalidade explícita, não upgrade global.

## Expected blast radius

Allowlist de implementação:

- `pyproject.toml` e `uv.lock`.
- `apps/core/tests/test_security_runtime.py`, novo contrato de pisos/paridade.
- `apps/botauth/tests/test_security_upgrade_compatibility.py`, novo, se necessário
  para cobrir lacuna HTTP demonstrada sem duplicar a suíte existente.

Evidência/configuração operacional temporária: `temp/security-hardening/s2/`.
Não editar modelos, migrations, permissões, settings de segurança, contratos
OIDC, fixtures clínicas, Dockerfile, CI ou Compose. Uma correção de aplicação
necessária precisa de ampliação explícita da allowlist antes de implementar.

## Failing-before plan

Registrar RED por pisos/paridade dos três alvos usando metadados instalados
reais, não mocks da versão. Usar casos sintéticos válidos/inválidos nos
endpoints existentes e conservar asserções de permissão/CSRF. Falha de import,
resolver ou ambiente não é evidência de regressão funcional corrigida.

## Implementation constraints

Respeitar série Django e AppConfig AutoField existentes. Não criar migrations
de fornecedor, trocar `DEFAULT_AUTO_FIELD` nem relaxar CSRF para obter verde.
Resolver só os três alvos e transientes necessários; qualquer alteração de
família fora do alvo exige evidência e escalada antes de ser aceita.

Usar Python/uv somente via `docker exec eqmd_dev`. Não mutar dependências do
container em execução. Para GREEN, requerer rebuild/recriação local aprovada,
sem startup que aplique migrations automaticamente. Sem ambiente paritário,
o slice está bloqueado, não pronto por passar a suite antiga.

## Validation

### Focused validation

```bash
./scripts/test.sh apps.core.tests.test_security_runtime
./scripts/test.sh apps.accounts apps.botauth apps.core
```

Se criar o módulo adicional, ele deve ser descoberto e executado no comando
de app. Tocar teste Python exige Ruff e typecheck no escopo conforme a política.

Dentro do container dev atualizado:

```bash
docker exec eqmd_dev uv lock --check
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

### Project-required gates

Aplicar `AGENTS.md`, incluindo `./scripts/test.sh`, lint e gates estáticos no
escopo. Não instalar tooling ausente para converter bloqueio em sucesso.

### Runtime/verification evidence

- Comparação declaração → lock → METADATA/versão instalada dos três alvos.
- Diff do lock por pacote, dependência que exigiu alteração e versões finais.
- Autenticação, acesso indevido, CSRF, JSON e OIDC com dados sintéticos.
- Zero migration nova/drift; igualdade das versões Pillow/pypdf anteriores.
- Atualização não habilita email real, integrações, bots ou sincronizações.

## Acceptance criteria

- [ ] R1: três pisos atendidos; Django 5.2 e Pillow anterior preservados.
- [ ] R2: ambiente atualizado e paridade exata, não só minor Django.
- [ ] R3: gates HTTP/segurança, suite e drift verdes sem alterar schema.
- [ ] R4: diff seletivo explicado; nenhum upgrade de família escondido.

## Escalation conditions

Retornar `BLOCKED_NEEDS_DECISION` se faltar wheel/resolução, houver dependência
incompatível, migration nova, contrato de autenticação diferente, necessidade
de código fora da allowlist, teste pré-existente quebrado ou ausência de
aprovação para reconstruir o ambiente. Não afrouxar piso/assertions ou instalar
versão alternativa silenciosamente. Não iniciar S3a.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-eqmd-sec-002-report.md`.

Incluir R1–R4 → evidências, RED/GREEN, versões antigas/novas, diff de resolução,
comandos/exit status, ambiente realmente testado, drift, limites e rollback.
Usar apenas dados sintéticos e agregados.

## Worker handoff

Implement only this approved slice after S1b acceptance. Reconstruct context
from the references, follow repository policy and the allowlist, and produce
the evidence report. Do not update tasks.md, commit, push, publish, deploy,
archive or start another slice. Stop as BLOCKED_NEEDS_DECISION for any new
decision; otherwise finish READY_FOR_REVIEW and REPORT_PATH.
