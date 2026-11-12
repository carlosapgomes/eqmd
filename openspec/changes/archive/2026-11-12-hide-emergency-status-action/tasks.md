# Tasks: hide-emergency-status-action

## 1. Preparação

- [x] 1.1 Confirmar com grep as referências atuais (tupla EMERGENCY em
      `patient_tags.py`, modal em `admission_section.html`)
- [x] 1.2 Congelar lista de arquivos do slice para evitar scope creep

## 2. Slice 01 — Ocultar botão Emergência do perfil do paciente

- [x] 2.1 Escrever/ajustar testes RED: ação de emergência ausente da lista de
      ações; demais ações preservadas
- [x] 2.2 Remover a tupla `Patient.Status.EMERGENCY` de `status_transitions`
      em `available_status_actions` (`patient_tags.py`)
- [x] 2.3 Remover a entrada morta `EMERGENCY: 'emergency_admission'` do mapa
      `_get_action_name` e a entrada `EMERGENCY: "Emergência"` de
      `expected_labels` no teste de labels
- [x] 2.4 Remover o bloco do modal `emergency_admissionModal` de
      `admission_section.html`
- [x] 2.5 Rodar verificação: testes da template tag + testes de backend de
      emergência inalterados
- [x] 2.6 Confirmar que nada de backend foi modificado
      (`git diff --stat` limitado aos 3 arquivos do slice)

## 3. Fechamento

- [x] 3.1 Executar `markdownlint-cli2` se algum `.md` foi alterado
      (nenhum `.md` lintável alterado; `openspec/changes/**` é coberto pelo
      `.markdownlintignore`)
- [x] 3.2 Atualizar este `tasks.md` marcando os itens concluídos
