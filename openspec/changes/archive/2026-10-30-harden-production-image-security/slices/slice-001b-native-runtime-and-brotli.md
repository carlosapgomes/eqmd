# S1b — Runtime nativo e Brotli corrigido

## Identity

- Change: `harden-production-image-security`.
- Slice: `eqmd-sec-001b`; tasks 1.3–1.5 de `../tasks.md`.
- Pré-condição: S1a aceito e comandos de build local aprovados; não iniciado.

## Objective

Entregar imagem local Python 3.12/Debian 13 com Brotli corrigido, cache de
instalação não persistente e funcionalidades nativas preservadas.

## Read first

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- `../proposal.md`, `../design.md`, decisões D2/D4/D5 e rollback.
- `../specs/production-image-security/spec.md`, `../evidence/baseline.json`.
- ADR-0001/ADR-0004 em `docs/adr/` e relatório aceito S1a.
- `Dockerfile`, `.dockerignore`, `Dockerfile.synapse`, `docker-compose.yml`.
- `scripts/tests/test_security_image_build.mjs`, criado em S1a.

## Requirements

- R1: base segue Python 3.12/Debian 13 e Brotli instalado é, por comparação
  dpkg, no mínimo `1.1.0-2+deb13u1`; manifesto/base exatos são registrados.
- R2: cache de instalação Python não persiste; pacotes necessários permanecem
  instalados nas mesmas versões do lock inicial, sem mudanças Python.
- R3: FFmpeg, Poppler, health check e targets necessários permanecem funcionais;
  o gate de contexto S1a continua verde.
- R4: o scan verifica o alvo Brotli e o relatório identifica este candidato como
  intermediário ainda não corrigido para os alvos de S2/S3a.

## Expected blast radius

Allowlist de implementação:

- `Dockerfile`.
- `scripts/tests/test_security_image_build.mjs`, estender controles nativos/cache.

Evidência/configuração temporária aprovada: `temp/security-hardening/s1b/`.
Não alterar `.dockerignore`, pyproject, lock, Compose, CI ou aplicação.
Regressão das regras de S1a deve retornar bloqueio, não ser consertada por
expansão silenciosa desta allowlist.

## Failing-before plan

Demonstrar piso Brotli ausente pela baseline portátil e manifesto antigo;
provar cache persistente no artefato anterior quando disponível. Adicionar
regressão do gate nativo/cache e registrar sua falha contra a construção antiga.
Não usar ausência de arquivo/teste como RED. S1a já resolveu o contexto: não
reconstruir o projeto com regras anteriores para reproduzir vazamento.

## Implementation constraints

Aplicar D2 preservando Python/lock e a distribuição. APT sem correção disponível,
nova ABI, patch compilado ou troca de distribuição exigem decisão. Não remover
bibliotecas/recursos só para reduzir alertas, nem limpar caches do host.

Antes de rebuild/recriação dev, aprovar plano local sem startup `migrate`, como
exige D4. Não instalar pacotes em runtime para validar um Dockerfile que não
foi construído. Preservar dados dev; nada no Eon/origem.

## Validation

### Focused validation

```bash
node --test scripts/tests/test_security_image_build.mjs
```

Inspeção executável de imagem real deve verificar versão via dpkg, manifesto,
cache ausente e metadados Python, além das sentinelas/controles S1a. Mock de
versão ou simples leitura de Dockerfile não substitui esse gate.

### Project-required gates

Seguir `AGENTS.md`, incluindo `./scripts/test.sh` e lint de Markdown tocado.
Mudança nativa exige evidência em runtime construído do novo Dockerfile;
suíte em imagem antiga não prova compatibilidade da nova base. Recriação local
sem aprovação é bloqueio, não permissão implícita de `compose up`.

### Runtime/verification evidence

- Identidade local/OCI sem confundir config e manifest digest, base e dpkg.
- Verificação de cache e pacotes instalados; lock Python sem diff.
- Smoke sintético de FFmpeg/Poppler e recursos dos targets existentes.
- Scan válido confirma tratamento do advisory Brotli; outros alertas continuam
  registrados como intermediários, sem risco aceito ou promoção de imagem.

## Acceptance criteria

- [ ] R1: Brotli corrigido e base/manifesto auditáveis na imagem construída.
- [ ] R2: cache ausente, instalação presente, lock/versões Python preservados.
- [ ] R3: gates S1a, recursos nativos e gates do projeto passam.
- [ ] R4: scan Brotli e limitações intermediárias documentados, sem deploy.

## Escalation conditions

Retornar `BLOCKED_NEEDS_DECISION` por falta de patch/ABI/target, aprovação local,
ferramenta ou scan válido; quebra de contexto S1a; arquivo extra ou decisão
nova de produto, arquitetura, segurança ou persistência. Não antecipar S2.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-eqmd-sec-001b-report.md`.

Incluir status, R1–R4 → evidência, arquivos, RED/GREEN, comandos/exit status,
versões/manifestos, runtime realmente usado, autorizações, limitações,
expansão inesperada/decisões humanas e rollback do Dockerfile/testes.

## Worker handoff

Implement only this approved slice after S1a acceptance. Reconstruct context
from the references, follow repository policy and the allowlist, run focused
and project gates and produce the evidence report. Do not update tasks.md,
commit, push, publish, deploy, merge, archive or start another slice.
Stop BLOCKED_NEEDS_DECISION for any new decision; otherwise finish
READY_FOR_REVIEW and REPORT_PATH. Await independent review.
