# ADR-0002: Application-level duplicate prevention, deferred DB constraint

## Status

Accepted (decisão do owner, 2026-08-30)

> **Transição encerrada em 2026-08-31**: consolidação executada na
> produção pelo owner (plano `fix-2026-08-31`, 43 grupos / 92 linhas /
> 49 ações, pós-checagem zero); `0003` aplicada com preflight
> re-verificando; as três camadas de proteção estão ativas. O script
> `upgrade-rootless-transition.sh` pode ser aposentado no próximo
> upgrade (ele mesmo detectará o zero e executará migrate completo).

## Contexto

O change `harden-patient-identity-and-duplicate-prevention` entregou
proteção contra pacientes duplicados em três camadas: aplicação
(slices 001-003: revisão advisory nome+nascimento, conflitos fortes
CPF/CNS com checksum oficial, e reserva canônica de número de
prontuário em todos os fluxos interativos), banco (slice 004:
constraint funcional única por tempo de vida sobre
`Lower(Trim(record_number))`, migração `0003`) e preflight de migração
(fail-closed enquanto houver colisões). A auditoria sem PII encontrou
40 grupos de colisão canônica (86 linhas) no banco restaurado. O change
`consolidate-historical-record-number-collisions` entregou o tooling
auditado de consolidação, mas a execução operatorial exige decisões
clínicas por grupo; 35 grupos estão decididos no plano do owner e 5
grupos mistos (pacientes distintos) aguardam decisão.

A equipe continua criando pacientes duplicados em produção. O owner
decidiu priorizar a proteção imediata e adiar a deduplicação histórica.

## Decisao

1. Deployar o código atual de produção **com as migrações `patients`
   retidas em `0001_initial`** (`manage.py migrate patients
0001_initial`; nunca `migrate` sem alvo neste deploy, pois `0003`
   aborta fail-closed nas 40 colisões — por design).
2. A proteção contra novos duplicados vigora pelas camadas de
   aplicação (todas as interfaces interativas: criação, trocas regular
   e rápida, update, admin).
3. A aplicação da `0002` (widen, metadata-only) é segura antes ou
   depois, mas não é necessária neste deploy.
4. A constraint (`0003`) fica **diferida** até a consolidação atingir
   zero (change `consolidate-historical-record-number-collisions`,
   tarefas 3.1/3.2 em aberto), seguindo o runbook em qualquer ambiente.
5. Escritas fora das interfaces interativas (comandos de import/sync e
   ORM direto) seguem desprotegidas até a `0003`.

## Alternativas Consideradas

1. Aguardar a deduplicação completa antes do deploy: rejeitada pelo
   owner — a equipe segue criando duplicados enquanto as 5 decisões
   clínicas pendentes não são tomadas; o custo de adiamento é diário.
2. Enfraquecer o preflight da `0003` para aplicar a constraint com
   colisões existentes (ex.: `USING` com filtro): rejeitada — violaria
   o requisito de unicidade por tempo de vida e abriria exceção
   permanente no modelo de dados clínico.
3. Deployar apenas os slices 001-003 sem o tooling de consolidação:
   rejeitada — o tooling é inerte até execução operatorial e seu
   versionamento junto evita divergência entre código e runbook.

## Consequencias

### Positivas

- A equipe é impedida de criar novos duplicados por todas as vias
  interativas imediatamente após o deploy.
- O fail-closed da `0003` continua protegendo contra aplicação
  acidental da constraint sobre dados não consolidados.
- O trabalho de decisão já feito (35 grupos no plano do owner) é
  preservado para a consolidação futura.

### Negativas/Trade-offs

- Imports/sync e ORM direto permanecem caminhos desprotegidos até a
  `0003`; se esses comandos rodarem em produção, a auditoria deve ser
  re-executada antes da consolidação.
- O deploy exige comando de migrate com alvo explícito enquanto a
  `0003` estiver pendente (risco de pipeline que roda `migrate` sem
  alvo falhar no preflight — visível e seguro, mas operacionalmente
  ruidoso).

### Riscos e Mitigacoes

- Pipeline de deploy roda `migrate` sem alvo e falha na `0003`:
  mitigado por esta ADR documentar o alvo explícito **e pelo script de
  transição `upgrade-rootless-transition.sh`**, que aplica o alvo
  automaticamente, aplica as demais apps normalmente e detecta o fim da
  transição via auditoria agregada (zero → `migrate` completo); a falha,
  se ocorrer, é limpa (transação revertida) e não corrompe estado.
- Dados novos em produção tornam o plano atual obsoleto: mitigado pelo
  runbook exigir re-auditoria e regeneração do plano por ambiente
  antes da execução.
- Esquecimento de longa data da `0003` pendente: mitigado pelas
  tarefas 3.1/3.2 do change de consolidação permanecerem abertas e
  pelo guard de `showmigrations` no fechamento futuro.
