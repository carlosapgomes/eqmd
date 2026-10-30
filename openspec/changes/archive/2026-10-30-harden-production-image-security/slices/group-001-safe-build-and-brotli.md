# Família S1 — Contexto seguro e runtime nativo

**Índice de planejamento, não contrato executável.** O slice original S1 foi
decomposto em contratos com aceites independentes. Seus requisitos foram
distribuídos sem alterar objetivo, pisos ou fronteira de arquitetura.
O trabalho externo abortado foi reconciliado conforme `../slice-review.md`.

## Contratos ativos

1. [S1a — Contexto de build seguro](slice-001a-safe-build-context.md).
2. [S1b — Runtime nativo e Brotli](slice-001b-native-runtime-and-brotli.md).

S1a comprova exclusão de dados privados em fixture isolada sem precisar alterar
o Dockerfile ou atualizar a base. Seu aceite libera a possibilidade de build
real seguro em S1b, sujeito à autorização operacional já exigida no design.

S1b corrige base/Brotli/cache e prova o artefato instalado. Ele não precisa
resolver falhas de contexto e mudanças nativas simultaneamente. Cada contrato
tem seu RED, teste de ponta a ponta, gates e relatório independente.

Sequência obrigatória: S1a → revisão → S1b → revisão → S2.
Não executar ambos por receber apenas autorização genérica para a família S1.
