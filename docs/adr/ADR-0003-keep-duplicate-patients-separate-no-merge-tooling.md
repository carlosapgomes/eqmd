# ADR-0003: Manter cadastros duplicados separados, sem merge clínico

## Status

Accepted (decisão do owner, 2026-09-01)

## Contexto

O endurecimento de identidade (`harden-patient-identity-and-duplicate-prevention`)
e a consolidação de prontuários (`consolidate-historical-record-number-collisions`,
executada na produção em 2026-08-31) deixaram o sistema com: prevenção
de duplicados em três camadas na criação (revisão advisory
nome+nascimento, conflitos fortes CPF/CNS com checksum oficial,
reserva vitalícia de número de prontuário no banco), e uma trilha de
auditoria para os duplicados históricos de **pessoa** (mesmo humano,
dois cadastros): números correntes da série `DUP-####`, marcadores
`::voided::` por linha e o sinalizador de "provável mesma pessoa"
(nome e nascimento idênticos) na revisão de colisões.

Os designs desses changes deferiram explicitamente um change futuro
`merge-duplicate-patients` para re-unificar cadastros duplicados.
Esta ADR registra a decisão sobre esse change.

O merge clínico significaria migrar todo o conteúdo FK-linked de um
paciente para outro (eventos, prescrições, formulários PDF, notas,
timeline, histórico de prontuário) com integridade referencial,
tombstone do cadastro absorvido e sem perder trilha de auditoria —
um subsistema clínico de alto risco.

## Decisão

**Não construir merge clínico.** Cadastros duplicados de pessoa
permanecem como registros separados e permanentes. A estratégia
permanece **prevenção + visibilidade**:

1. Prevenção na criação (as três camadas já em produção) impede que
   novos duplicados entrem pelas vias interativas.
2. Os duplicados históricos ficam identificados pela trilha
   `DUP-####` (número corrente) e pelo sinalizador de mesma pessoa;
   a equipe consulta os dois cadastros lado a lado quando atende um
   desses pacientes.
3. Nenhum cadastro é deletado ou absorvido automaticamente —
   histórico clínico é imutável por princípio do projeto.

## Alternativas consideradas

1. **Tooling de merge completo** (migrar conteúdo + tombstone):
   - Vantagens: prontuário único por pessoa; relatórios sem
     dupla-contagem.
   - Desvantagens: migração de conteúdo clínico entre FKs é o
     operation de maior risco do domínio; um merge errado é
     praticamente irreversível; subsistema grande para construir,
     testar e manter.
   - Por que não: avaliação do owner — risco alto para poucos
     pacientes afetados e benefício pequeno.

2. **Soft-link apenas** (banner na UI: "possível duplicado de X",
   com link para o outro cadastro):
   - Vantagens: barato; melhora a consulta sem tocar dados.
   - Desvantagens: mais uma superfície de UI clínica para manter.
   - Por que não agora: a trilha `DUP-####` + revisão de colisões
     já dão a visibilidade necessária; revisitável se a dor
     operacional aparecer (decisão reversível sem custo afundado).

3. **Deleção manual do cadastro duplicado**:
   - Rejeitada sem análise — destrói histórico clínico (atalho
     destrutivo já documentado como fora de política nos designs de
     consolidação).

## Consequências

### Positivas

- Risco zero de corromper histórico clínico por merge indevido.
- Nenhum subsistema novo para construir, verificar ou manter.
- Trilha de auditoria preservada exatamente como está.

### Negativas / trade-offs

- Pacientes duplicados têm dois cadastros; a equipe precisa
  consultar ambos ao atendê-los.
- Relatórios/agregações por pessoa podem dupla-contar esses casos
  (mitigação: identificáveis pela série `DUP-####`).

### Riscos e mitigações

- **Novo duplicado de pessoa escapa da revisão advisory**: o operador
  pode ignorar o aviso nome+nascimento e não há CPF/CNS obrigatório.
  Mitigação: a revisão de criação sinaliza; a descoberta de colisões
  e o sinalizador de mesma pessoa evidenciam o caso; é a postura
  operacional aceita desde o design do slice 001.
- **Dor operacional cresce com o tempo**: revisitar pela alternativa
  2 (soft-link), registrada aqui como caminho de menor risco.

## Referências cruzadas

- `openspec/changes/archive/2026-08-31-consolidate-historical-record-number-collisions/`
  (backlog item que deferia o merge; desfecho registrado aqui)
- `openspec/changes/archive/2026-08-31-harden-patient-identity-and-duplicate-prevention/`
- [ADR-0002](ADR-0002-deploy-application-level-duplicate-prevention-with-deferred-database-constraint.md)
  (transição de deploy que tornou a prevenção possível)
