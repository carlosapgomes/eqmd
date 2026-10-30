# harden-production-image-security

Correção de segurança delimitada da imagem produtiva antes da migração de host.
Status: **planejamento revisado; nenhuma implementação feita nesta revisão**.

## Contrato

- [Proposal](proposal.md): objetivo, cinco componentes e limites.
- [Design](design.md): versões, build, paridade, risco residual e rollback.
- [Spec](specs/production-image-security/spec.md): requisitos verificáveis.
- [Tasks](tasks.md): 0/14 tasks; controle do reviewer/coordenador.
- [Revisão de dimensionamento](slice-review.md): divisão e rastreabilidade.
- [Baseline portátil](evidence/baseline.json): identidade, métricas e 101
  matches-alvo, sem secrets, dados clínicos ou dependência do `temp/` original.
- [ADR-0004 Proposed][adr]: fronteira de remediação e aceite.

[adr]: ../../../docs/adr/ADR-0004-bounded-production-image-security-remediation.md

## Sequência de cinco unidades executáveis

1. [S1a — Contexto seguro](slices/slice-001a-safe-build-context.md).
2. [S1b — Runtime/Brotli](slices/slice-001b-native-runtime-and-brotli.md).
3. [S2 — HTTP/TLS](slices/slice-002-http-and-tls-dependencies.md).
4. [S3a — Pillow](slices/slice-003a-pillow-compatibility.md).
5. [S3b — Qualificação](slices/slice-003b-artifact-qualification.md).

S1 e S3 continuam nomes de famílias. Seus mapas `slices/group-001-*.md` e
`slices/group-003-*.md` são índices, não outros slices. Os contratos únicos
anteriores de S1/S3 foram substituídos antes de qualquer implementação.

Cada unidade exige autorização específica, failing-before apropriado, gates,
relatório e revisão antes da próxima. Build/recriação local precisam de plano
operacional autorizado. Este planejamento não autoriza executá-los agora.

## Handoff para implementador

Leia `AGENTS.md`, proposal, design, spec e somente o contrato da unidade aprovada.
Comece exclusivamente pelo S1a após autorização explícita. Não execute S1a/S1b
em uma rodada por receber o nome da família S1. Não atualize tasks, faça
commits/push, publique imagens ou toque origem/Eon. Use o path de relatório
definido no contrato e pare para revisão independente.

## Validação do planejamento

```bash
openspec validate harden-production-image-security --type change \
  --strict --no-interactive
openspec status --change harden-production-image-security
markdownlint-cli2 'openspec/changes/harden-production-image-security/**/*.md' \
  docs/adr/ADR-0004-bounded-production-image-security-remediation.md \
  docs/adr/README.md
```

A validação destes artefatos não afirma que dependências, imagem ou produção
foram corrigidas. Os checks de código/scan pertencem à implementação futura.

## Git e evidências

O repositório já ignora `openspec/changes/*/`. Este change existe localmente e
é reconhecido pelo OpenSpec, mas não aparecerá no status Git normal. Nenhuma
regra de ignore foi alterada. Para versionar, o operador precisará incluir
explicitamente os artefatos ignorados, além da ADR/índice, pela sua via normal.
Não versionar scans brutos, cache, dumps ou credenciais para contornar isso.
