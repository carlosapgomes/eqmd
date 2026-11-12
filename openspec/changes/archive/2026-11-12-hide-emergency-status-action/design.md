# Design — hide-emergency-status-action

## Contexto

A seção "Status & Gerenciamento de Internação" do perfil do paciente
(`patient_detail.html` → partial `admission_section.html`) renderiza botões de
ação gerados pela template tag `available_status_actions`
(`apps/patients/templatetags/patient_tags.py`). A transição
`Patient.Status.EMERGENCY` é uma dessas ações. Cada botão abre um modal no
mesmo partial; o modal de emergência é `#emergency_admissionModal`.

Superfícies de UI mapeadas (grep em templates, templatetags, assets):

- Botão: gerado somente em `available_status_actions`; única renderização em
  `admission_section.html`; único include desse partial é
  `patient_detail.html`. Nenhuma outra página.
- Modal: `admission_section.html` (linhas ~289-336), inalcançável sem o botão.
- Não confundir (ficam de fora): filtro "Emergência" em `patient_list.html`,
  badge `patient_status_badge`, alerta "Paciente em Emergência", opção
  "Emergência" em "Tipo de Internação".

## Decisões

### D1 — Ocultar na fonte única de geração (template tag), não por CSS

Remover a tupla `EMERGENCY` de `status_transitions` em
`available_status_actions` em vez de esconder com CSS ou condicional no
template. Motivo: a tag é o único ponto de geração do botão; a remoção ali
elimina a ação de todas as renderizações atuais e futuras sem deixar código
morto de apresentação.

### D2 — Remover o modal órfão junto com o botão

Sem o botão (`data-bs-target="#emergency_admissionModal"`), o modal nunca pode
ser aberto; mantê-lo é HTML morto na página. A remoção é apenas de marcação de
apresentação — o formulário POST dele aponta para a rota
`emergency_admission`, que permanece registrada e funcional.

### D3 — Backend 100% preservado (reversibilidade)

Nada é removido de views, URLs, formulários, signals ou permissões. A rota
`patients/<uuid>/status/emergency/` continua respondendo; os testes de view
(`test_status_changes.py::...emergency_admission_view_success`) e de
formulário (`test_forms.py::test_emergency_admission_*`) devem passar sem
nenhuma alteração — isso é a prova de que o backend ficou intacto. Reativar o
botão no futuro exige apenas um revert deste slice.

### D4 — Pacientes com status "Em Emergência" existentes

A tag já omite a ação para o status corrente (`status_value != current_status`),
portanto pacientes atualmente em emergência continuam vendo as demais ações
(Internar, Dar Alta etc.) e o alerta de emergência permanece exibindo o estado
atual. Nenhuma migração de dados é necessária.

## Riscos e mitigação

- Risco: algum teste existente esperar a ação de emergência na lista.
  Mitigação: `test_available_status_actions_outpatient` será ajustado no
  próprio slice (TDD, vermelho → verde) para afirmar ausência.
- Risco: dependência oculta do modal em JS. Mitigação: grep confirmou que
  nenhum script referencia `emergency_admissionModal`.

## Estratégia de testes

- Unitário da template tag: `available_status_actions` não inclui
  `Patient.Status.EMERGENCY` para paciente ambulatorial (status base do teste).
- Unitário da template tag: demais ações continuam presentes (regressão).
- Render do partial não é testado diretamente (sem suite de template atual);
  a ausência do botão na UI decorre deterministicamente da ausência da tupla
  (fonte única, D1).
- Testes de backend de emergência existentes devem passar inalterados (D3).
