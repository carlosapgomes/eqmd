## 1. Slice 01 - Backend obrigatório, validado e atômico

- [x] 1.1 Ler `AGENTS.md`, `docs/workflows/coding-standards.md`,
      `design.md`, `specs/patients/spec.md` e `slices/slice-01.md`
- [x] 1.2 Escrever testes primeiro para obrigatoriedade, validação, criação do
      `PatientRecordNumber` e rollback transacional
- [x] 1.3 Tornar `PatientForm.initial_record_number` obrigatório
- [x] 1.4 Adicionar `PatientForm.clean_initial_record_number()` reutilizando
      `validate_record_number_format`
- [x] 1.5 Garantir persistência atômica de `Patient` + `PatientRecordNumber`
- [x] 1.6 Atualizar testes existentes afetados no menor escopo possível
- [x] 1.7 Validar comando: `./scripts/test.sh apps.patients`
- [x] 1.8 Parar e reportar resultado da slice

## 2. Slice 02 - UI exclusiva de criação e relatório final

- [x] 2.1 Ler `AGENTS.md`, `docs/workflows/coding-standards.md`,
      `design.md`, `specs/patients/spec.md` e `slices/slice-02.md`
- [x] 2.2 Escrever testes primeiro para renderização no create, ausência no
      update e update ignorando POST inesperado de `initial_record_number`
- [x] 2.3 Renderizar seção "Prontuário Hospitalar" somente em
      `patient_create.html`
- [x] 2.4 Não alterar `patient_update.html`
- [x] 2.5 Executar verificação focada: `./scripts/test.sh apps.patients`
- [x] 2.6 Executar verificação final: `./scripts/test.sh`
- [x] 2.7 Criar `/tmp/add-initial-patient-record-number-on-create-report.md`
      com resumo, arquivos alterados, testes e checklist de aceite
- [x] 2.8 Parar e reportar resultado da slice

## 3. Slice 03 - Alinhar testes ao prontuário obrigatório

- [x] 3.1 Ler `AGENTS.md`, `docs/workflows/coding-standards.md`,
      `design.md`, `specs/patients/spec.md` e `slices/slice-03.md`
- [x] 3.2 Rodar `./scripts/test.sh apps.patients` para identificar falhas de
      testes desatualizados por ausência de `initial_record_number`
- [x] 3.3 Atualizar somente testes/payloads de criação via formulário para
      incluir `initial_record_number` válido
- [x] 3.4 Não alterar código de produção
- [x] 3.5 Rodar `./scripts/test.sh apps.patients`
- [x] 3.6 Se passar, rodar `./scripts/test.sh`
- [x] 3.7 Atualizar `/tmp/add-initial-patient-record-number-on-create-report.md`
      com a seção `Slice 03 - Test Alignment`
- [x] 3.8 Parar e reportar resultado final do change
