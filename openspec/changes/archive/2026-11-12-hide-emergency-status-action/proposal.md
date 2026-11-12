# Proposal: hide-emergency-status-action

## Why

O botão `Emergência` da seção "Status & Gerenciamento de Internação" do perfil
do paciente não tem função útil no momento:

- ele apenas troca a flag de status para "Em Emergência", sem criar registro de
  internação (`PatientAdmission`) nem registrar o motivo digitado (o campo
  `reason` do formulário é descartado pela view);
- ele pode levar a estados inconsistentes (paciente internado com admissão
  ativa marcado como "Em Emergência" sem encerrar a internação);
- o fluxo clínico corrente usa `Internar` (admissão formal com tipo de
  admissão "Emergência") e `Transferir Internamente` para cobrir as mesmas
  necessidades.

Pesquisa de superfície de UI confirmou que o botão aparece em **um único
ponto**: o perfil do paciente (`patient_detail.html` inclui o partial
`admission_section.html`), gerado pela template tag `available_status_actions`
(`apps/patients/templatetags/patient_tags.py`). Nenhuma outra página renderiza
essa ação.

O objetivo deste change é apenas ocultar o botão da interface. O backend
(view, URL, formulário, signals) permanece intacto e testado, permitendo
reativar a ação no futuro se o fluxo de pronto-socorro voltar a fazer sentido.

## What Changes

- Remover a transição `EMERGENCY` da lista `status_transitions` da template
  tag `available_status_actions`, fazendo o botão `Emergência` desaparecer do
  perfil do paciente (única superfície onde é renderizado).
- Remover o modal órfão `emergency_admissionModal` do partial
  `admission_section.html` (sem o botão-gatilho, o modal é HTML inalcançável).
- Ajustar os testes da template tag para o novo contrato: a ação de emergência
  NÃO é oferecida para nenhum status.

## Capabilities

### Added Capabilities

- `patient-status-actions`: define quais ações de mudança de status o perfil do
  paciente expõe; a ação de admissão de emergência deixa de ser exposta,
  enquanto as demais ações (Internar, Dar Alta, Ambulatorial, Declarar Óbito,
  Transferir Internamente) e o endpoint de emergência permanecem intactos.

## Não-escopo explícito (não mexer)

- `EmergencyAdmissionView`, rota `emergency_admission`,
  `EmergencyAdmissionForm` e signals — backend permanece funcional.
- Testes de view/form de emergência (`test_status_changes.py`,
  `test_forms.py`) — continuam válidos e devem passar sem alteração.
- Filtro de status "Emergência" na lista de pacientes
  (`patient_list.html`) — é filtro de busca, não ação.
- Badge de status `patient_status_badge` (inclui "Emergência") — exibe estado
  atual, não é ação.
- Alerta "Paciente em Emergência" no perfil — exibição passiva de estado.
- Opção "Emergência" no campo "Tipo de Internação" do modal `Internar` —
  conceito distinto (tipo de admissão formal).
