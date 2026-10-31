# eon-migration Specification

## Purpose

Contrato verificável da etapa 1 da migração de produção EQMD para o
servidor eon: artefatos implantáveis (Compose, roles PostgreSQL 15,
frontend, cronjobs, runbook de cutover) com baseline imutável por
digest, topologia isolada, restore ensaiado e execução produtiva
inteiramente gated por comandos exatos aprovados. Implementada pela
change arquivada `2026-10-30-migrate-production-to-eon`.

## Requirements

### Requirement: Baseline de imagem imutável

O deployment do eon SHALL referenciar a imagem da aplicação
exclusivamente por digest
`ghcr.io/carlosapgomes/eqmd@sha256:fe31d296...`, e qualquer falha de
pull SHALL abortar o procedimento sem acionar build local.

#### Scenario: pull falha no destino

- **WHEN** o pull do digest falhar durante preparação ou cutover
- **THEN** o procedimento para com erro
- **AND** nenhum build local é executado como fallback

### Requirement: Topologia de rede isolada

O Compose do eon SHALL usar apenas as redes `hospital_*_eqmd`
(ingress/app/db/egress) com memberships mínimos, declarando as redes
compartilhadas como externas, e SHALL NOT publicar portas do
PostgreSQL ou do gunicorn no host.

#### Scenario: validação estática da topologia

- **WHEN** `docker compose config` é executado com env sintético
- **THEN** apenas memberships previstos aparecem
- **AND** nenhum publish de porta de banco/aplicação existe

### Requirement: Banco dedicado com privilégios mínimos

O PostgreSQL 15 do eon SHALL recriar a database com encoding UTF8,
collation e ctype `C`, extensões `unaccent` e `pg_trgm`, role de
runtime sem superusuário e identidade separada de migrator; a
migração de dados SHALL ser exclusivamente lógica (dump/restore).

#### Scenario: restore com roles mínimas

- **WHEN** o restore conclui e a aplicação sobe
- **THEN** a role da aplicação não é superusuária
- **AND** `migrate` executa apenas com a identidade migrator

### Requirement: Restore ensaiado com evidências

Todo fluxo de migração de dados SHALL ser ensaiado localmente com
dados sintéticos, produzindo manifesto com hashes conferidos, contagens
agregadas de objetos e tempos medidos por etapa.

#### Scenario: rehearsal local

- **WHEN** o ensaio e2e executa
- **THEN** hashes do manifesto conferem nas duas pontas
- **AND** tempos por etapa alimentam o plano da janela

### Requirement: Agendamentos com origem única

Os cinco cronjobs SHALL existir no destino com mecanismo de lock,
timezone validado e execução única, e SHALL permanecer suspensos até
o aceite do cutover; a sincronização Firebase SHALL permanecer
desativada.

#### Scenario: reativação pós-aceite

- **WHEN** o aceite do cutover é registrado
- **THEN** os jobs são reativados apenas no destino
- **AND** a origem permanece sem execução de jobs

### Requirement: Runbook de cutover com gates e rollback

O cutover SHALL ser conduzido pelo runbook aprovado, com gates
binários E1–E9, horário-limite de aborto dentro da janela e
procedimentos distintos de rollback para antes e depois da primeira
escrita aceita no destino.

#### Scenario: primeira escrita aceita

- **WHEN** o destino recebe a primeira escrita de produção aceita
- **THEN** o runbook registra a mudança de regime de rollback
- **AND** o rollback passa a exigir backup consistente do destino

### Requirement: Configuração sem secrets no repositório

A configuração SHALL ser validável com valores sintéticos; arquivos
reais de ambiente SHALL ficar fora do Git e nenhuma saída de
`docker compose config` com valores reais SHALL ser registrada em
evidência.

#### Scenario: validação sintética

- **WHEN** a validação estática do Compose roda
- **THEN** utiliza somente o env sintético versionado
- **AND** nenhum secret aparece em artefatos ou logs
