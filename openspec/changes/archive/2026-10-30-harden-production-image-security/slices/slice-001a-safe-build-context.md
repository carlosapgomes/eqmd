# S1a — Contexto de build seguro

## Identity

- Change: `harden-production-image-security`.
- Slice: `eqmd-sec-001a`; tasks 1.1–1.2 de `../tasks.md`.
- Status: não iniciado; autorização de implementação/teste Docker pendente.

## Objective

Comprovar que o contexto enviado ao builder exclui dados privados e evidências,
preservando os recursos necessários, antes de qualquer rebuild do projeto.

## Read first

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- `../proposal.md`, `../design.md`, D2 e limites de autorização D4/D5.
- `../specs/production-image-security/spec.md`, requisito de contexto privado.
- `.dockerignore`, `Dockerfile`, `Dockerfile.synapse`, `docker-compose.yml`.
- `scripts/tests/test_image_scan_workflow.mjs` como convenção Node existente.

## Requirements

- R1: nomes/caminhos proibidos não chegam ao contexto construído: `.env*`,
  credenciais, chaves privadas, backups, logs/mídia locais e `temp/`.
- R2: o teste usa somente sentinelas sintéticas e prova a semântica real de
  build/COPY; não apenas regex das regras ou inspeção visual do arquivo.
- R3: código/recursos legítimos necessários aos targets permanecem incluídos;
  a correção não exclui módulos Matrix por sua funcionalidade estar inativa.
- R4: não há alteração de imagem base, pacotes, cache do runtime ou ambiente dev.

## Expected blast radius

Allowlist de implementação:

- `.dockerignore`.
- `scripts/tests/test_security_image_build.mjs`, novo, inicialmente de contexto.

Fixtures, Dockerfile de prova e saídas: `temp/security-hardening/s1a/`.
O Dockerfile de prova pertence à fixture e não substitui o Dockerfile do projeto.
Leitura dos targets existentes é permitida; não editar Dockerfile, lock,
pyproject, Compose, CI ou aplicação. Caminho adicional exige escalada.

## Failing-before plan

TDD: criar fixture mínima copiando as regras vigentes, sentinelas proibidas e
arquivos permitidos representativos. Construir artefato isolado e inspecionar
seu conteúdo sem executar a aplicação. A regra anterior deve permitir ao menos
uma sentinela proibida e a asserção deve falhar por esse motivo.

Não enviar o workspace real, secrets verdadeiros ou gigabytes do cache para
reproduzir o problema. Falha por Docker ausente ou import não é RED válido.

## Implementation constraints

Apenas exclusões mínimas justificadas. Evitar glob que remova recursos de código
ou ignore por acaso o próprio fixture. Registrar quais sentinelas ficaram fora
e quais recursos-controle ficaram dentro. Não criar Dockerfile específico por
target, mecanismo de secret novo ou outra decisão arquitetural.

Pedir autorização para o teste Docker local exato. Não construir a imagem
completa do projeto, recriar `eqmd_dev`, aplicar migrations ou limpar caches.
Seguir a política de engenharia em `AGENTS.md`, sem refatoração especulativa.

## Validation

### Focused validation

```bash
node --test scripts/tests/test_security_image_build.mjs
```

A prova real não pode virar skip quando Docker estiver indisponível. Registrar
bloqueio nesse caso. Garantir falha se uma regra de exclusão relevante regredir.

### Project-required gates

Aplicar `AGENTS.md`, incluindo `./scripts/test.sh` e lint de Markdown tocado.
Como Dockerfile/dependências não mudam, não há motivo para rebuild do dev aqui.
Essa suíte não prova Brotli corrigido; tal evidência pertence a S1b.

### Runtime/verification evidence

Artefato isolado da fixture: identidades, sentinelas ausentes, controles
presentes e comandos com exit status. Confirmar ausência de diff em Dockerfile,
pyproject e lock. Sem acesso a dados reais ou containers de produção.

## Acceptance criteria

- [ ] R1: todos os grupos de caminhos proibidos estão cobertos e excluídos.
- [ ] R2: RED/GREEN exercita o builder real em fixture somente sintética.
- [ ] R3: controles necessários continuam presentes no artefato inspecionado.
- [ ] R4: nenhuma mudança nativa, de lock ou de ambiente foi executada.

## Escalation conditions

Retornar `BLOCKED_NEEDS_DECISION` se faltar autorização/ferramenta, houver
conflito entre exclusão e recurso legítimo, necessidade de regra por target,
arquivo fora da allowlist, contradição do spec ou decisão nova de segurança.
Não ampliar o contrato, saltar a prova real ou iniciar S1b.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-eqmd-sec-001a-report.md`.

Incluir status, R1–R4 → evidência, arquivos, failing-before, passing-after,
comandos/exit status, identidade e conteúdo agregado da fixture, limitações,
expansão inesperada/decisões humanas e rollback das regras/testes do slice.

## Worker handoff

Implement only this approved slice. Reconstruct context from the references.
Follow repository policy, preserve the allowlist, produce failing-before and
passing-after evidence, run the required gates and write the report.
Do not update tasks.md, commit, push, publish, deploy, merge, archive or start
another slice. Stop BLOCKED_NEEDS_DECISION for any new decision; otherwise
return READY_FOR_REVIEW and REPORT_PATH. Await independent review.
