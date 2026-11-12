# patient-status-actions Specification

## ADDED Requirements

### Requirement: Patient profile status actions exclude emergency admission

O perfil do paciente SHALL NOT expor a ação de mudança de status
`Emergência` (`EmergencyAdmissionForm` / `emergency_admission`) na seção
"Status & Gerenciamento de Internação".

#### Scenario: Emergency action is not offered for outpatient patients

- **WHEN** a template tag `available_status_actions` é avaliada para um
  paciente ambulatorial e qualquer usuário autenticado com acesso ao paciente
- **THEN** a lista de ações retornada não contém ação com status
  `Patient.Status.EMERGENCY`
- **AND** a lista continua contendo as ações `Internar` (INPATIENT),
  `Dar Alta` (DISCHARGED), `Ambulatorial` (OUTPATIENT) e
  `Declarar Óbito` (DECEASED) quando aplicável ao status corrente

#### Scenario: Emergency action is not offered for inpatient patients

- **WHEN** a template tag `available_status_actions` é avaliada para um
  paciente internado
- **THEN** a lista de ações retornada não contém ação com status
  `Patient.Status.EMERGENCY`

#### Scenario: Emergency modal is not present in the admission section

- **WHEN** o partial `admission_section.html` é renderizado
- **THEN** não existe elemento com id `emergency_admissionModal`
- **AND** não existe formulário apontando para a URL `emergency_admission`

### Requirement: Emergency admission backend remains functional

O backend de admissão de emergência SHALL permanecer registrado e funcional
após a ocultação da ação na interface.

#### Scenario: Emergency endpoint still accepts POST

- **WHEN** um POST válido é enviado para a rota
  `patients/<uuid:pk>/status/emergency/` por um usuário autenticado com acesso
  ao paciente
- **THEN** o status do paciente muda para `Patient.Status.EMERGENCY`
- **AND** os testes existentes de view e formulário de emergência passam sem
  alteração
