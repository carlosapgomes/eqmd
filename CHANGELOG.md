# Changelog

All notable changes to this project are documented in this file.
The format is based on Keep a Changelog, and the project adheres to
Semantic Versioning.

## [Unreleased]

## [0.8.0] - 2026-11-19

### Added — exportação XLSX do mapa de enfermaria

- **Exportação XLSX do mapa de enfermagem** (change
  `add-ward-map-xlsx-export`; `a4ed537`, `81e9a0b`, `f31164f`,
  `c35f977`): novo serviço `ward_map_export.py` transforma as
  linhas já resolvidas do mapa em um workbook XLSX — uma aba
  por enfermaria sobrevivente, colunas fixas `Leito`,
  `Identificação`, `Médico/Interno`, `Evolução` e `Conduta` com
  larguras fixas aprovadas. O endpoint de exportação reusa a
  resolução completa de contexto da view do mapa, de modo que o
  download é exatamente o resultado atual de busca/filtro, e
  responde como attachment (a página permanece em
  `/patients/map`). Botão `Exportar xlsx` acima dos resultados e
  fora do formulário de filtro, desabilitado somente quando o
  resultado filtrado não tem pacientes; os anchors de exportação
  são marcados como download para não disparar o overlay global
  de navegação (`c35f977`). Apenas a evolução publicada mais
  recente é exportada (rascunhos e notas excluídas fora;
  autor/conteúdo em branco quando o paciente não tem nota
  publicada).

### Added — cópia fragmentada no card da evolução

- **Diálogo de cópia fragmentada no card da evolução** (change
  `add-dailynote-card-copy-dialog`; `621ceff`): o botão de
  copiar do card da DailyNote ganha fluxo próprio via hook
  `copy-dailynote-btn` servido por novos módulos webpack.
  Conteúdo até 4.000 caracteres copia direto como hoje (sem
  diálogo); acima disso abre diálogo Bootstrap 5 com
  "Copiar tudo" e botões numerados `P1..P4`. A divisão é
  client-side em fronteiras de parágrafo, alvo de ~3.900
  caracteres por parte com teto de 4.000 e no máximo 4 botões;
  cada botão exibe sua contagem de caracteres e mantém indicador
  de copiado enquanto o diálogo está aberto. Quando as quatro
  partes não cobrem o conteúdo todo, o diálogo mostra aviso
  explícito com total e caracteres cobertos (a capacidade de
  16.000 caracteres do hospital é citada quando excedida) — o
  conteúdo nunca é truncado em silêncio. Helpers de clipboard
  compartilhados com o fluxo genérico de cards (`showToast` e
  `showClipboardFeedback` movidos verbatim de
  `assets/index.js` para `assets/js/clipboard-utils.js`;
  `copyTextToClipboard(text)` derivado do corpo do
  `copyToClipboard(button)` existente), com o fluxo genérico
  preservado. O algoritmo de divisão é coberto por harness Node
  automatizado dentro da suíte Django (precedente
  `page_navigation_loading_harness.cjs`) e o bundle webpack foi
  reconstruído (`static/main-bundle.js`).

### Docs — specs OpenSpec (novas capacidades)

- Specs **novas** (`dailynote-card-copy`, `patient-map-export`)
  formalizam os dois contratos; dois changes arquivados em
  `openspec/changes/archive/2026-11-19-*`.

## [0.7.0] - 2026-11-18

### Added — descoberta e classificação de modelos de laudo

- **Classificação opcional de modelos de laudo por tags do catálogo**
  (change `add-report-template-tag-discovery`; `9f73b44`):
  editores autorizados podem associar zero ou mais tags **existentes**
  do catálogo ao criar/editar um modelo de laudo — novo campo
  `ReportTemplate.tags` (M2M para `patients.AllowedTag`, migration
  `reports/0004_reporttemplate_tags`, trilha de histórico
  `simple-history` preservada). O formulário nunca cria tags novas;
  propriedade, exceções administrativas de edição e visibilidade
  público/privado permanecem inalteradas; templates existentes
  ficam sem tags até classificação autorizada (predicados ativos
  excluem modelos não classificados; limpar filtros os restaura).
  Auditoria técnica da associação fica na camada de dados, sem nova
  tela de histórico.

- **Filtragem por tags e busca dinâmica no catálogo e no seletor**
  (change `add-report-template-tag-discovery`; `9c7c65d`,
  `bb71267`): `/reports/templates/` e o seletor de modelos usado
  na criação do laudo do paciente ganham filtragem por tags e
  busca por nome, reutilizando da lista/mapa de pacientes as
  preferências salvas de especialidade, o fallback principal, os
  modos ANY/ALL e a semântica explícita de limpar/reaplicar;
  metadados de tags restritas seguem ocultos independentemente do
  acesso ao modelo.

### Changed — UX de filtros de tags (pacientes e modelos)

- **Política explícita de filtros unificada** (change
  `improve-tag-filter-discovery-ux`; `ea546d7`, `7a3f6d8`,
  `31bfe44`, `37c1172`): separa o predicado aplicado, os controles
  em edição (rascunho) e a preferência de especialidade
  persistida, sinalizando quando diferem. O predicado só é
  aplicado pela ação explícita **Aplicar filtros** — digitar
  nome, alterar seleção de tags/modo ou alternar alas vazias não
  atualiza resultados implicitamente. Remoção de badge,
  limpar/reaplicar e paginação são atalhos deliberados sobre o
  último estado aplicado, nunca commitando edições pendentes
  não relacionadas. Rótulos distinguem coleção genuinamente
  vazia de coleção esvaziada pelo filtro ativo.

- **Barras de ação únicas na lista e no mapa de pacientes**
  (changes `simplify-patient-list-filter-actions` e
  `simplify-patient-map-filter-actions`; `0f8532c`, `6fd95d6`):
  uma única barra de ação por página — Aplicar filtros, Limpar
  todos os filtros (clear-all verdadeiro) e restauração do
  padrão de tags da especialidade com escopo nomeado; links
  duplicados de limpar/restaurar removidos; resumos aplicados
  tornam-se informativos, inclusive em estados vazios filtrados;
  o mapa preserva busca, ala e visão de enfermaria vazia
  aplicadas ao restaurar tags, um Apply vazio suprime
  explicitamente os defaults automáticos e o texto diferencia
  ala vazia de ala sem pacientes correspondentes (página cheia e
  fragmento AJAX).

- **Editor de tags do modelo com chips pesquisáveis** (change
  `improve-report-template-tag-editor-ux`; `0a2a560`): criação e
  edição de modelo trocam o `select multiple` nativo
  (Ctrl/Cmd-click) por seleção pesquisável local nas tags
  autorizadas ao editor, com chips selecionados e botão de
  remoção nomeado em cada chip (inclusive o último); as edições
  de tags ficam pendentes até Criar/Salvar Modelo, preservando
  nome, markdown, switches e demais valores não salvos; contrato
  POST, links protegidos, regras de propriedade e fallback
  nativo sem JS mantidos.

- **Catálogo de modelos: barra única e overlay só em navegação
  real** (change `simplify-report-template-filter-actions`;
  `0a2a560`, `198071d`): `/reports/templates/` recebe a barra
  alinhada à esquerda com o mesmo vocabulário da lista de
  pacientes; Limpar todos remove nome/tags/opções e suprime
  defaults no reload; Restaurar recupera nome e tags/modo
  aplicados descartando rascunhos; essas duas ações reconstróem
  os controles via navegação GET completa, enquanto Apply e
  paginação mantêm o transporte AJAX; o overlay global de
  carregamento passa a distinguir navegação real de interações
  AJAX canceladas — exatamente um overlay, sem o bloqueio de
  15 s anterior; URLs legadas de query preservadas.

### Fixed — renderização dos filtros de tags

- **Assets versionados e cartões de filtro responsivos** (change
  `fix-tag-filter-rendering`; `94fd66a`): URLs com versão de
  conteúdo para o stylesheet e scripts compartilhados de filtro
  impedem que JavaScript legado em cache oculte o novo contêiner
  de resultados no primeiro carregamento; resultados ancorados
  diretamente abaixo do campo de busca, linhas de filtro
  responsivas e espaçosas com área de ação separada; comentários
  inline Django multilinha inválidos substituídos por blocos.

### Docs — specs OpenSpec

- Specs **nova** (`page-navigation-feedback`) e **atualizadas**
  (`patient-tag-filtering`, `reports`) formalizam o contrato de
  filtragem por tags, a política explícita de aplicação e o
  feedback de navegação; sete changes arquivados em
  `openspec/changes/archive/2026-11-1*`.

## [0.6.0] - 2026-11-12

### Added — patient profile clinical safety

- **Ação de status Emergência oculta do perfil do paciente**
  (change `hide-emergency-status-action`; `7ea7972`): o botão
  `Emergência` da seção "Status & Gerenciamento de Internação"
  apenas trocava a flag de status — sem criar `PatientAdmission`,
  descartava o motivo digitado (campo `reason` do formulário
  ignorado pela view) e permitia estados inconsistentes (paciente
  internado com admissão ativa marcado "Em Emergência"). Os fluxos
  `Internar` (admissão formal com tipo "Emergência") e
  `Transferir Internamente` cobrem a mesma necessidade. A
  transição `EMERGENCY` sai da template tag
  `available_status_actions` (única superfície de UI onde era
  renderizada) e o modal órfão `emergency_admissionModal` do
  partial `admission_section.html` é removido; o backend (view,
  URL, formulário, signals) permanece intacto e testado,
  permitindo reativação futura. Nova spec `patient-status-actions`
  em `openspec/specs/`; testes da template tag ajustados ao novo
  contrato (emergência não oferecida para nenhum status).

- **Exclusão clínica de paciente restrita ao admin Django** (change
  `restrict-patient-delete-to-admin`; `b1e15ca`): o botão
  `Excluir` do perfil/lista devolvia `405 Method Not Allowed`
  (a view só implementava `post()`, mas as entradas eram links
  GET) e um `POST` forjado com `deletion_reason` por médico
  soft-deletava qualquer paciente. Agora `PatientDeleteView`
  exige superuser — `403` para autenticados não-superuser
  (incluindo médicos com `patients.delete_patient`), espelhando o
  `PatientRestoreView` já existente; os anchors `Excluir` saem de
  `patient_detail.html` e `patient_list.html` (sem atalho clínico,
  nem para superuser) e o template órfão
  `patient_confirm_delete.html` é removido. O bulk action do
  Django admin permanece o caminho suportado de exclusão. Nova
  spec `patient-delete` em `openspec/specs/`; +13 testes focados
  (403 médico/staff, soft-delete e reason vazio para superuser,
  GET 405/redirects, HTML sem controle `Excluir` preservando
  timeline/edição).

### Changed — deploy docs

- **Plano de upgrade do PostgreSQL 15 para 18** (`c528187`): novo
  `docs/deployment/postgres-18-upgrade-plan.md` com dry-run
  completo (dump de 1,6 GB, restore em PG 18.6 efêmero,
  `migrate --check`, suíte integral aprovada no 18.6). Conclusão:
  upgrade viável, exigindo um ajuste de código quando executado
  (a migration `drugtemplates/0007` quebra ao rodar do zero no PG
  18, avaliador de funções SQL mais estrito) e com risco
  operacional principal no novo `PGDATA` da imagem oficial 18.
  Apenas documentação — produção permanece no PostgreSQL 15 nesta
  release.

## [0.5.1] - 2026-11-08

### Fixed — deploy upgrade script

- **Upgrade por tag aceita grafias com/sem prefixo `v`**
  (`37fea62`): o CI (`docker/metadata-action type=semver`)
  publica tags sem o `v` (ex: `0.5.0`), mas `upgrade.sh`/runbook
  esperavam `vX.Y.Z` — nenhuma imagem com `v` existia no GHCR e o
  upgrade por tag morria em silêncio (`2>/dev/null` + pipefail +
  `set -e` encerravam o script na atribuição do digest, antes do
  `fail()` e do trap ERR). O script agora tenta a grafia recebida
  e também a sem `v` (fallback), com `|| true` no pipeline para o
  `fail()` reportar a mensagem; o workflow passa a publicar também
  a grafia `v{{version}}` (mantém a sem prefixo por
  compatibilidade); runbook documenta as duas grafias aceitas.

### Fixed — landing page copy

- **Textos da landing page sem alegações de segurança não
  verificáveis** (`775bd15`): remove "Segurança Total",
  "criptografia" e "auditoria completa"; substitui por
  "Controle de acesso", "Histórico de alterações" e "Suporte
  direto" com descrições factuais (autenticação, permissões por
  perfil, rastreabilidade). Descrição do PWA/manifest e meta
  `description` passam a "acompanhamento de pacientes".
  Cobertura: 5 testes de copy (`assertContains`/`assertNotContains`
  para os textos novos e as alegações removidas).

### Changed — docs

- **Guia de migração de domínio** (`27c299e`): branding atualizado
  e formatação revisada (sem mudanças de código ou comportamento).

## [0.5.0] - 2026-11-07

### Added — student draft supervision

- **Supervisão de rascunhos de estudante** (change
  `add-student-draft-supervision`; S1 `6052532`, S2–S7 `4fe836a`
  atômicas por design D13): estudantes criam rascunhos supervisionados
  em todo o app — timeline humana com badge/idade/tinta e filtro de
  rascunhos, PDF detail legível com negação de output, finalização de
  alta bloqueada para rascunho pendente, rollout end-to-end para
  SimpleNote/DailyNote/H&P (incl. negação de PDF/impressão), rascunhos
  de mídia com limpeza de arquivo em hard delete, receita com
  finalização ortogonal ao status, consentimento sem arquivos e
  imutabilidade inclusiva de rascunhos, round trip de update de PDF
  (hospital + APAC) e verificação de ativação com permissões exatas,
  auditoria e dry-run de rollback. Núcleo de permissão draft-aware
  (can_edit/can_delete_event sem limite de 24h para rascunhos
  humanos, regra pós-final de quatro casos, backstop em
  `Event.save()`).

### Added — SUS exam request batch (chequinho)

- **Solicitação de exames em lote** (change
  `exam-request-batch-chequinho`; S1 `098e99f`, S2 `4a9e724`,
  S3 `602d675`, docs/ADR `5e3f67f`, UX `cb62cca`): página dedicada
  com campos compartilhados (motivo/data/médico com auto-fill atual)
  e formset dinâmico de 1–12 exames criando uma
  `PDFFormSubmission` por exame em transação, todas com o mesmo
  `batch_id`; supervisão com paridade APAC (rascunho/definitivo);
  download do lote compondo até **3 vias por folha A4** com linha de
  corte tracejada (`ceil(N/3)` páginas); ações de lote na timeline e
  no detalhe com ícone bi-stack padronizado. Guia de fluxo e ADR de
  impressão 3-up documentados.

### Added — timeline attribution and copy

- **Atribuição de criador/aprovador nos cards** (`0aa7057`, change
  `add-approval-attribution-display`): rodapé do card renderiza
  `created_by` (+profissão) com checagem coerente; metadados de
  aprovação passam a ser exibidos.
- **Copiar conteúdo do relatório de alta** (`97aeac0`):
  `DischargeReport.get_copy_text()` exporta texto puro (cabeçalho de
  especialidade, datas de internação/alta com permanência, 7 seções
  rotuladas na ordem do PDF, seções vazias omitidas) com botão de
  clipboard no card da timeline e no detalhe.

### Security — protected media serving

- **Mídia protegida por autenticação** (change
  `serve-protected-media`, `c106916`): produção (`DEBUG=False`) não
  tinha rota `/media/` enquanto o nginx faz proxy para o Django —
  todo `FileField.url` cru retornava 404. Superfícies agora são
  servidas por views autenticadas: preview de template PDF
  (`template/<uuid>/preview/`), anexos de termo de consentimento
  assinado (`attachments/<uuid>/serve/`, `events.view_event` +
  acesso ao paciente) e previews admin de mídia via
  `get_thumbnail_url()` do FilePond com reparo mínimo de refs
  obsoletas.

### Added — deploy and verification tooling

- **Upgrade de produção EON** (`26efbd1`): script `upgrade.sh`
  (tags resolvidas para digests, backup primeiro, migrate com gate,
  health check estrito) + runbook de upgrade.
- **Skill de verificação no navegador** (`93a733f`): harness
  Playwright + Chrome do sistema (`verify-eqmd`) que dirige a stack
  dev real para provar comportamento UI/UX ponta a ponta
  (rascunhos de estudante, aprovação médica, chequinho, alta/APAC).

### Changed — housekeeping

- `.gitignore`: ignora `.pi/subagents/` e versiona config do MCP
  chrome-devtools (`915635f`).

## [0.4.1] - 2026-11-03

### Changed — legal content

- **Termos de uso atualizados** (`6dae3cb`): revisão completa do
  texto exibido na página de termos de uso (sem mudanças de código
  ou de comportamento).

## [0.4.0] - 2026-11-03

### Fixed — test suite stability

- **Suíte de testes 100% verde** (change
  `isolate-sample-specialty-seed-from-tests`): a migração de dados
  de especialidades amostrais (accounts 0005) passa a semear
  somente quando `EQMD_SEED_SAMPLE_SPECIALTIES` é verdadeiro
  (padrão `True`; bancos já migrados intactos) e o
  `config/test_settings.py` desativa o seed — os 74 erros
  pré-existentes por colisão de chave única desaparecem, a suíte
  completa (3378 testes) passa e o job full-suite do CI é
  desbloqueado. Canário cobre as 30 abreviações do bootstrap.

### Added — document duplication across the timeline

- **Duplicação de documentos** (changes `extend-document-duplication`,
  `duplicate-discharge-report`, `duplicate-consent-form`):
  - **Relatório**: botão duplicar no card da timeline abre formulário
    pré-preenchido (título e conteúdo, data de hoje); a cópia é
    independente e editável na própria janela de 24h.
  - **Receita**: botão duplicar também no card da timeline (antes só
    no detalhe) — POST cria rascunho pré-preenchido e abre a edição.
  - **Relatório de alta**: a cópia nasce rascunho (mesmo a partir de
    final expirado); salvar como definitivo carimba finalização
    apenas na cópia; a fonte permanece intacta.
  - **Termo de consentimento**: o texto congelado do original abre
    editável com a data do documento auto-substituída pela atual
    (`dd/mm/aaaa`, substituição única); template do original fixo
    como proveniência (aceita inativo); sem anexos e sem referência
    cruzada.
  - Testes de regressão POST para os três apps de texto e namespaces
    de URL curtos (`dailynotes:`, `simplenotes:`,
    `historyandphysicals:`).

### Added — specialty team tag governance

- **Governança de tags por equipe de especialidade** (change
  `add-specialty-team-tag-governance`): membership com ciclo de vida
  auditado, catálogo governado, atribuições de tags de paciente com
  política e auditoria, leitores privacy-safe, página de tags do
  líder responsável, filtro multi-tag com busca na lista de
  pacientes, preferências de filtro por especialidade e paridade de
  filtro no mapa de enfermaria. Tags existentes são preservadas e
  classificadas como públicas ou customizadas, sem inferência de
  equipe. Migrações: accounts 0006–0008, events
  0006–0007 (com backfill), patients 0004–0005.

### Changed — discharge report hardening

- **Relatório de alta endurecido** (change
  `harden-discharge-report-collaborative-draft`): predicado
  colaborativo único (model, view e timeline), guardrails de
  identidade clínica em rascunhos colaborativos e janela de correção
  de 24h ancorada na finalização (legado: `created_at`). Migração:
  dischargereports 0003.

### Changed — tag selector and PWA

- Resultados compactos e acessíveis no seletor de tags
  (`role="list"` explícito).
- Título da home-screen desacoplado do ambiente via
  `PWA_SHORT_NAME`/`PWA_NAME`.

### Security — production image and infra hardening

- **Imagem de produção** (change `harden-production-image-security`):
  contexto de build seguro, base Brotli corrigida, floors de
  dependências (Django/DRF/certifi/Pillow) e qualificação final da
  imagem.
- **Infraestrutura**: artefatos de deploy parametrizados, detalhes de
  infra removidos dos artefatos, infra-guard (pre-commit + CI),
  política de segurança publicada e scan de imagem CI com uploads
  SARIF reparados.

### Added — EON migration stage 1

- **Migração EON** (change `eon-migration`): artefatos stage-1
  (compose, IPAM, ambiente sintético), papéis/init/restore do PostgreSQL
  15, cron UTC com locks, runbook de cutover com rollback e checklist
  de aceitação, ensaio e2e com timings, spec publicada e ADR-0005 e
  atualizações phase-D (alias Caddy, cron Bahia, variáveis do site).

## [0.3.2] - 2026-10-12

### Added — prescription duplication

- **Receita: duplicar para nova receita**
  (change `2026-10-12-duplicate-outpatient-prescription`):
  - Botão "Duplicar" na receita (rascunho ou finalizada) cria uma
    cópia como novo rascunho do mesmo paciente — instruções e itens
    copiados como linhas independentes, data local de hoje, autor é
    quem duplicou — e abre a edição da cópia para ajustes.
  - Itens copiados sem `source_template`: duplicar nunca infla
    `DrugTemplate.usage_count`. Requer `events.add_event` + acesso ao
    paciente; ação somente POST; sem migração.

## [0.3.1] - 2026-09-20

Backfill: tag `v0.3.1` (`5e44785`) publicada sem entrada de changelog.

### Changed — release pipeline

- Publicação de imagens versionadas (CI build-and-push).

## [0.3.0] - 2026-09-20

Backfill: tag `v0.3.0` (`f384e92`) publicada sem entrada de changelog.

### Fixed — PDF headers

- Cabeçalhos PDF compartilhados passaram a acomodar nomes longos de
  paciente.

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
