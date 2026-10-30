# S3a — Pillow e compatibilidade de mídia

## Identity

- Change: `harden-production-image-security`.
- Slice: `eqmd-sec-003a`; tasks 3.1–3.3 de `../tasks.md`.
- Pré-condição: S2 aceito e S3a autorizado; não iniciado.

## Objective

Entregar Pillow 13 em ambiente lock-backed e candidato identificado, preservando
processamento de imagem, PDF/vídeo e proteção dos arquivos.

## Read first

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- `../proposal.md`, `../design.md`, D1/D3/D4 e limites D5/D6.
- `../specs/production-image-security/spec.md`, `../evidence/baseline.json`.
- ADR-0001/ADR-0004 e relatórios aceitos S1a/S1b/S2.
- `pyproject.toml`, `uv.lock`, `Dockerfile`.
- `apps/mediafiles/image_processor.py`, `validators.py`, `models.py`.
- `apps/mediafiles/tests/test_security.py`, `test_validators.py`, `test_views.py`.
- `apps/pdf_forms/services/pdf_overlay.py`, `apps/pdf_forms/tests/test_services.py`.
- `apps/core/tests/test_security_runtime.py`, introduzido em S2.

## Requirements

- R1: Pillow `>=13.0.0,<14` instalado e exatamente paritário ao lock, sem mudar
  pypdf ou outras famílias por iniciativa própria.
- R2: JPEG/PNG/WebP, modos relevantes, inválidos, thumbnails e PDF continuam
  corretos; arquivo protegido, acesso negado e vídeo não regridem.
- R3: construir candidato com todos os pisos instalados e preservar S1a/S1b/S2;
  registrar sua identidade, fonte e paridade com o ambiente de teste.
- R4: não adiar testes desta atualização para S3b nem chamar a conclusão
  funcional de aceite de segurança, publicação ou implantação.

## Expected blast radius

Allowlist de implementação:

- `pyproject.toml` e `uv.lock`.
- `apps/core/tests/test_security_runtime.py`, estender contrato com Pillow.
- `apps/mediafiles/tests/test_image_security_compatibility.py`, novo.
- `apps/pdf_forms/tests/test_security_runtime_compatibility.py`, novo somente
  para lacuna demonstrada do contrato de imagem/overlay.

Configuração/evidência operacional temporária: `temp/security-hardening/s3a/`.
Não editar parsers produtivos, modelos, migrations, CI, Dockerfile, Compose ou
criar documentação de aceite final. Ajuste produtivo de compatibilidade exige
ampliação explícita da allowlist antes de implementar; não redesenhar parsers.

## Failing-before plan

TDD para piso Pillow sobre metadados instalados reais no runtime S2. Cobrir
formatos permitidos/negados com fixtures sintéticas em memória e registrar
comportamento antes da troca de major. Helper inexistente não é RED válido.

O scan anterior demonstra a exposição, mas não substitui regressão funcional.
Não executar PoC destrutiva/RCE, arquivos clínicos ou requisições em produção.

## Implementation constraints

Seguir D1/D4: atualização seletiva e rebuild autorizado do lock, sem instalação
ad hoc no runtime. Não relaxar validação/permissões, permitir formato novo ou
atualizar pypdf para 6 para obter testes verdes. Conflito exige revisão.

Todos os testes funcionais devidos a Pillow devem terminar aqui. Registrar
candidato final de implementação com versão instalada, identidade local/OCI,
HEAD/estado das fontes e configuração relevante para S3b verificá-lo. Não
inventar RepoDigest GHCR nem iniciar comparação residual completa neste slice.

## Validation

### Focused validation

```bash
./scripts/test.sh apps.core.tests.test_security_runtime
./scripts/test.sh apps.mediafiles.tests.test_image_security_compatibility
./scripts/test.sh apps.mediafiles apps.pdf_forms apps.pdfgenerator
```

Se criar módulo PDF adicional, ele deve ser descoberto no comando de app.
Dentro do dev reconstruído e autorizado:

```bash
docker exec eqmd_dev uv lock --check
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

### Project-required gates

Aplicar `AGENTS.md`, incluindo suíte completa, Ruff/typecheck dos módulos
alterados e lint Markdown. Não executar contra produção nem instalar tooling
para contornar ambiente ausente. Registrar skips sem criar waiver novo.

### Runtime/verification evidence

- Declaração → lock → instalação real de Pillow e demais pisos já introduzidos.
- Testes positivos/negativos de imagem, thumbnail, PDF e proteção de arquivos.
- Regressão de vídeo e zero drift/migration nova.
- Identidade/configuração do candidato, base e manifesto instalado, mantendo
  a prova S1a de contexto seguro e S1b de cache/Brotli.
- Manifesto de versão/referência das fontes e comandos necessários para o
  reviewer reconstituir a proveniência; não depender apenas de tag local.

## Acceptance criteria

- [ ] R1: Pillow 13/lock paritários e pypdf preservado.
- [ ] R2: contratos de mídia/PDF/vídeo e permissões comprovados nos gates.
- [ ] R3: candidato identificado e paritário, preservando requisitos anteriores.
- [ ] R4: regressão completa aqui; qualificação/aceite de segurança pendentes.

## Escalation conditions

Retornar `BLOCKED_NEEDS_DECISION` por incompatibilidade, schema/contrato novo,
resolução fora do envelope, ferramenta/ambiente/autorização ausentes ou mudança
fora da allowlist. Não reduzir piso/assertions ou deixar falha para S3b resolver.
Não executar publicação/deploy nem iniciar S3b após o relatório.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-eqmd-sec-003a-report.md`.

Incluir status, R1–R4 → evidência, arquivos, RED/GREEN, versões/lock, comandos e
exit status, regressão, imagem/fonte/ambiente realmente testados, limitações,
expansão inesperada/decisões humanas e rollback. Indicar a identidade do
candidato entregue para qualificação, sem alegar scan final aprovado.

## Worker handoff

Implement only this approved slice after S2 acceptance. Reconstruct context
from the references, preserve repository policy and the allowlist, run all
focused/project gates and write the report. Do not update tasks.md, commit,
push, publish, deploy, merge, archive or start another slice. Stop
BLOCKED_NEEDS_DECISION for any new decision; otherwise finish READY_FOR_REVIEW
and REPORT_PATH. Await independent review before S3b.
