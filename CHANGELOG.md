# Changelog

All notable changes to this project are documented in this file.
The format is based on Keep a Changelog, and the project adheres to
Semantic Versioning.

## [Unreleased]

## [0.2.1] - 2026-10-12

### Fixed — collaborative discharge drafts

- **Relatório de alta: rascunho colaborativo**
  (change `2026-10-12-fix-discharge-report-collaborative-draft`):
  - Qualquer médico/residente autenticado com acesso ao paciente pode
    editar e re-salvar como rascunho um relatório criado por outro
    usuário, sem limite de tempo; qualquer um deles pode finalizar
    (`Salvar Definitivo`).
  - Corrige duas causas: o helper de exibição comparava `user.profession`
    (inexistente no usuário) com constantes string, e a regra de edição
    exigia ser o criador ou ter `events.change_event`.
  - Relatórios finalizados mantêm a regra de 24h (somente criador);
    exclusão e criação inalteradas; não-médicos seguem bloqueados.
  - Cobertura: edição/finalização por segundo médico (inclui residente),
    rascunho com mais de 24h, negação a não-médicos, janela de finalizado.

## [0.2.0] - 2026-09-01

Release focada em integridade de identificação do paciente, registro
temporário e estabilidade operacional. Intervalo: `v0.1.0` (2026-01-01)
a `2dee5f5` (2026-09-01), 247 commits.

### Added

- **Registro temporário de paciente**
  (change `add-temporary-record-registration`):
  - Cadastro de paciente sem número definitivo: o sistema gera um número
    `TMP-XXXXXXXX` transacional e único, com motivo obrigatório registrado
    na trilha de auditoria.
  - Prefixo `TMP-` reservado: as quatro portas de escrita manual de número
    (criação, troca registrada, troca rápida e porta gerenciada) recusam
    valores digitados com o prefixo.
  - Banner de regularização no detalhe do paciente com formulário para o
    fluxo existente de troca rápida; o histórico de números é preservado.
  - Dashboard staff-only (`/patients/temporary-records/`) com pendências,
    idade em dias e agregado por criador.
- **Prevenção de duplicatas e integridade de identidade**
  (change `harden-patient-identity-and-duplicate-prevention`, ADR-0002):
  - Revisão de duplicatas por nome e data de nascimento no cadastro.
  - Conflitos fortes por CPF/CNS com evidência persistida.
  - Reserva de número de prontuário vitalícia em nível de aplicação.
  - Constraint PostgreSQL única vitalícia
    (`unique_patient_record_number_lifetime`).
  - Bloqueio de números placeholder em todas as portas de escrita
    (change `block-placeholder-record-numbers`).
  - Ferramenta auditorada de consolidação de colisões históricas, com
    runbook e relatório (changes `consolidate-historical-record-number-
collisions` e `split-consolidation-service-module`).
- **Termos de consentimento** (change `add-consent-forms`): templates de
  termo com versionamento, fluxo de evento, PDF, anexos (fotos e zip),
  exclusão e evento de timeline.
- **App de relatórios** (change `add-reports-app`): documentos clínicos a
  partir de templates com placeholders (inclui data da internação atual).
- **Pipeline de renderização markdown compartilhado**: dialeto
  `easymd_v1`, parser/IR e renderer HTML, adotado por relatórios e notas
  diárias (changes `unify-markdown-rendering-pipeline`).
- **Notas diárias e alta**: PDF compacto com idade no evento e internação
  ativa; PDF de alta com resultado final aprimorado e exclusão.
- **Formulários PDF**: duplicação configurável de formulários, campo de
  hora, auto-preenchimento por especialidade e busca dinâmica de
  procedimentos/medicamentos; card de timeline com ação de duplicata.
- **Timeline**: card de mudanças de perfil do paciente via signals e
  filtros em offcanvas.
- **Integrações**: mapeamento de ala no firebase-sync e correções de sync
  em produção; provisionamento Matrix e OIDC refinados.
- **Infra/DevOps**: script `upgrade-rootless.sh` com dry-run, backup e
  rollback automático; ambiente de desenvolvimento em Docker com container
  sandbox para o agente; Dockerfile configurável para matrix-synapse.

### Changed

- Ambiente de desenvolvimento restaurado e travado
  (changes `restore-green-development-quality-gates`,
  `stabilize-test-suite-lifecycle-gates`, `fix-date-boundary-suite-
flakiness`, ADR-0001): suíte determinística (2.780 testes, 25 skips
  conhecidos), gates `ruff`/`mypy`/`typecheck` fail-closed e CI bloqueante
  com suíte completa.
- Política de duplicatas: pacientes duplicados permanecem separados, sem
  ferramenta de merge clínico (ADR-0003).
- Especificações OpenSpec tornadas o cânone do sistema: 11 changes
  arquivados e specs vivas alinhadas à realidade.
- Número de prontuário inicial exigido na criação (posteriormente
  flexibilizado pelo fluxo temporário).

### Fixed

- Preservação de ala/leito na edição de paciente
  (change `fix-patient-update-location-preservation`).
- Sincronização de leito na transferência com internação ativa.
- Escopo de dia e âncoras de data independentes do fuso horário
  (flakiness de fronteira de data).
- Função SQL `unaccent` indisponível ao restaurar o banco (drugtemplates).
- Modais de edição de admissão restaurados no detalhe do paciente.
- Spinners e alinhamento nas buscas de medicamentos e pesquisas.
- Erros de startup de log e de sync de ala no firebase-sync.
- Abreviações de especialidades e tags de template quebrados no avatar.

### Security

- Estado temporário derivado do prefixo do número (sem coluna sensível
  nova); zero migrações no release do registro temporário.
- Dashboard de pendências restrito a `is_staff`; resposta 403 sem renderizar
  qualquer dado de paciente para não staff.

## [0.1.0] - 2026-01-01

Baseline inicial de produção: aplicações core (patients, dailynotes,
pdf-forms, reports, matrix, accounts) com pipeline de build em GHCR.
