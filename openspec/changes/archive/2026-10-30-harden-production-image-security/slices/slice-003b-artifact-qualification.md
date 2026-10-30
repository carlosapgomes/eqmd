# S3b — Qualificação de segurança do artefato

## Identity

- Change: `harden-production-image-security`.
- Slice: `eqmd-sec-003b`; tasks 3.4–3.6 de `../tasks.md`.
- Pré-condição: S3a aceito, candidato identificado e verificação local aprovada.
- Status: não iniciado; qualificação não é autorização de deploy.

## Objective

Entregar comparação auditável baseline/candidato e riscos residuais do artefato
exato, separando conclusão técnica de aceitação humana e promoção produtiva.

## Read first

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- `../proposal.md`, `../design.md`, D5/D6, precondições e rollback.
- `../specs/production-image-security/spec.md`, `../evidence/baseline.json`.
- ADR-0001/ADR-0004 e relatórios aceitos S1a/S1b/S2/S3a.
- `Dockerfile`, `.dockerignore`, `pyproject.toml`, `uv.lock` para conferência.
- Testes/manifestos produzidos nos slices anteriores e proveniência do candidato.

## Requirements

- R1: o artefato analisado é o candidato aceito em S3a, com fonte, identidade
  imutável, configuração e versões reais comprovadas, sem depender de tag móvel.
- R2: baseline e candidato são analisados com a mesma versão/base/política
  válida; todos os estados/supressões são distinguíveis e sem ignore novo.
- R3: cinco alvos estão corrigidos no artefato; 101 matches históricos são
  rastreáveis e novos advisories dos alvos também entram no gate.
- R4: residuais e diferenças materiais são relatados; nenhuma exceção, promoção,
  publicação ou implantação é aceita automaticamente pelo worker.

## Expected blast radius

Allowlist de escrita:

- `docs/security/production-image-security.md`, novo dossiê operacional conciso.
- Evidências/exports/manifestos/scans locais em `temp/security-hardening/s3b/`.

Não alterar Dockerfile, contexto, dependências, lock, aplicação, testes, CI ou
Compose. Falha descoberta aqui retorna evidência ao reviewer; não iniciar uma
correção escondida de qualquer slice anterior. Não publicar relatórios brutos
ou caches gigantes na documentação versionável.

## Failing-before plan

Usar a baseline portátil para identificar os alvos afetados e reproduzir o
scan de referência com a base válida escolhida, como exige D5. O resultado
anterior é a evidência de exposição; não é necessário fabricar teste unitário
que falhe para um slice somente de qualificação operacional.

Se o scan atual da baseline divergir do snapshot histórico, registrar os dois
e a causa conhecida/limitação, comparando o candidato apenas com a base atual
equivalente. Erro de rede/ferramenta não demonstra remoção de vulnerabilidade.

## Implementation constraints

Reutilizar o candidato identificado em S3a, conferindo que fontes/imagem não
mudaram. Reconstrução por perda do artefato exige autorização e renovação da
prova de identidade/regressão; não fabricar equivalência de imagens por tag.
Rebuild não autoriza editar código neste slice.

Scan local/OCI/registry conforme D5, com plano autorizado, sem privilégio de
socket desnecessário ou acesso à origem/Eon. Não usar `only-fixed`, desligar
validação de base, inserir VEX/ignore, ou aceitar risco em nome do operador.
Não reexecutar workloads de produção nem enviar email/dados reais.

## Validation

### Focused validation

Verificações operacionais explícitas do plano aprovado:

1. Conferir identidade do candidato, base, plataforma e versões instaladas
   contra os manifestos aceitos em S3a e o lock atual.
2. Executar scans baseline/candidato; exigir exit status de execução válido,
   JSON parseável, identidade correta e base equivalente ainda válida.
3. Comparar pacote/advisory/versão/fix-state, 101 matches de referência e novos
   advisories dos cinco alvos; confirmar não inclusão de dados/cache privados.
4. Entregar tabela de residuais, diferenças nativas/transitivas e limitações,
   sem transformar contagem menor ou exit 0 informativo em aceite de risco.

Não há script de scan novo presumido. Registrar comandos reais, formatos e
checks usados, conforme o mecanismo existente aprovado. Ausência de ferramenta,
identidade ou autorização produz bloqueio.

### Project-required gates

A mudança deste slice é documental/evidência: aplicar lint Markdown e checks
pertinentes de `AGENTS.md`. Conferir os resultados de suíte/check/drift de S3a
contra a mesma fonte/versões; não declarar que foram executados novamente se
apenas referenciados. Se houver rebuild, renovar os gates de runtime relevantes
antes de qualificar o novo artefato.

### Runtime/verification evidence

Comparação de imagens realmente analisadas, versão de scanner, base/hash/data,
versões instaladas, alvo corrigido, supressões padrão, mudanças residuais e
riscos materiais. Não inferir acesso explorável de cada match ou realizar PoC.
Usar metadados e agregados, sem dados clínicos/credenciais.

## Acceptance criteria

- [ ] R1: mesma imagem/fonte/regressão aceita em S3a, sem tag como única prova.
- [ ] R2: par de scans comparável e válido com todos os estados preservados.
- [ ] R3: cinco alvos sem versão afetada; comparação histórica/atual explícita.
- [ ] R4: dossiê residual pronto para reviewer/operador, sem aceite ou promoção.

## Escalation conditions

Retornar `BLOCKED_NEEDS_DECISION` se candidato não corresponder, alvo persistir,
houver novo advisory prioritário, scan não for equivalente/válido, faltar
artefato/ferramenta/autorização ou surgir nova implicação de segurança,
compatibilidade, arquitetura, persistência ou regra clínica. Não corrigir
código nem aceitar residual silenciosamente; parar e entregar a evidência.

## Evidence report

Path: `/tmp/<APP_VIZINHA>-slice-eqmd-sec-003b-report.md`.

Incluir status, R1–R4 → evidência, arquivos, exposição de referência e resultado
posterior, comandos/exit status, fonte/identidades, scans e gates efetivamente
executados versus herdados, residuais, limitações e decisões humanas. Indicar
como retomar a baseline local sem comandos destrutivos; não há deploy a reverter.

## Worker handoff

Execute only this approved qualification slice after S3a acceptance. Follow
repository policy and the exact allowlist, reconstruct context, run approved
verification and write the report. Do not update tasks.md, modify implementation,
commit, push, publish, deploy, merge, archive or accept risk. Stop
BLOCKED_NEEDS_DECISION for new decisions; otherwise finish READY_FOR_REVIEW
and REPORT_PATH. Await independent security and operator review.
