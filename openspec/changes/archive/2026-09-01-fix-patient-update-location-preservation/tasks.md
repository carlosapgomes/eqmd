# Tasks: fix patient update location preservation

## 1. Slice 01 - Preservar localização no update de perfil

- [x] 1.1 Reproduzir cenário: paciente internado perde ala/leito ao editar dados
      pessoais
- [x] 1.2 Criar `PatientProfileForm` sem `ward`/`bed`
- [x] 1.3 Atualizar `PatientUpdateView` para usar `PatientProfileForm`
- [x] 1.4 Adicionar teste de regressão para garantir preservação de `ward`/`bed`
      com admissão ativa
- [x] 1.5 Validar comando:
      `./scripts/test.sh apps.patients.tests.test_patient_profile_update_preserves_location`

## 2. Slice 02 - Sincronização de `ward` no signal de admissão

- [x] 2.1 Ajustar `update_patient_admission_status` para sincronizar `ward` em
      admissão ativa
- [x] 2.2 Manter sincronização existente de `bed`
- [x] 2.3 Adicionar teste de regressão para `ward` + `bed`
- [x] 2.4 Validar comando:
      `./scripts/test.sh apps.patients.tests.test_admission_signal_syncs_patient_location`

## 3. Verificação consolidada

- [x] 3.1 Rodar comando combinado dos dois módulos:

      ```bash
      ./scripts/test.sh \
        apps.patients.tests.test_patient_profile_update_preserves_location \
        apps.patients.tests.test_admission_signal_syncs_patient_location
      ```

- [x] 3.2 Registrar evidência de sucesso dos testes focados no handoff
