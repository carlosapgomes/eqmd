# Família S3 — Compatibilidade de mídia e qualificação do artefato

**Índice de planejamento, não contrato executável.** O slice original S3 foi
decomposto antes de qualquer implementação. Não há mudança de produto ou
aceite automático de risco decorrente dessa divisão.

## Contratos ativos

1. [S3a — Pillow e compatibilidade](slice-003a-pillow-compatibility.md).
2. [S3b — Qualificação do artefato](slice-003b-artifact-qualification.md).

S3a entrega a atualização de Pillow, os testes que ela exige e um candidato
identificado com regressão completa. Não deixa testes de compatibilidade
pendentes para S3b nem chama a conclusão local de aceite de segurança.

S3b entrega a comparação de segurança baseline/candidato e o dossiê de risco
residual do mesmo artefato. Não altera dependências ou código para consertar
problemas descobertos na qualificação; retorna bloqueio e evidência ao reviewer.

Sequência obrigatória: S2 aceito → S3a → revisão → S3b → revisão de segurança
→ decisão explícita do operador. Nenhum contrato autoriza publicar ou implantar.
