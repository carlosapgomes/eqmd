# Slice 01 Prompt - Backend obrigatório, validado e atômico

Implemente **somente** esta slice. Comece com contexto zero e leia os arquivos
na ordem indicada.

## Pre-read obrigatório

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `openspec/changes/add-initial-patient-record-number-on-create/design.md`
4. `openspec/changes/add-initial-patient-record-number-on-create/specs/patients/spec.md`
5. `openspec/changes/add-initial-patient-record-number-on-create/slices/slice-01.md`

## Objetivo

Fazer o backend da criação de paciente exigir, validar e salvar o número inicial
de prontuário hospitalar (`PatientRecordNumber`) com atomicidade.

## Arquivos permitidos

- `apps/patients/forms.py`
- `apps/patients/tests/test_forms.py`
- Opcional, se necessário para teste mais claro:
  - `apps/patients/tests/test_initial_record_number_create.py` (novo)

Não toque em templates nesta slice.

## TDD obrigatório

Escreva/ajuste testes antes de implementar:

- criação sem `initial_record_number` é inválida;
- formato inválido é rejeitado com o validador existente;
- criação válida salva `PatientRecordNumber` atual ligado ao paciente;
- `Patient.current_record_number` é atualizado;
- falha simulada ao criar `PatientRecordNumber` faz rollback do `Patient`.

## Regras de implementação

- Reutilize `validate_record_number_format`; não duplique regras.
- Use `transaction.atomic()` no menor escopo possível.
- Mantenha `PatientProfileForm` intocado.
- Não altere views ou templates nesta slice, salvo se um teste provar que é
  indispensável; se isso acontecer, pare e peça orientação.
- Não faça refatorações não relacionadas.

## Verificação obrigatória

Execute:

```bash
./scripts/test.sh apps.patients
```

## Critérios de aceite

- Todos os testes da slice passam.
- `PatientForm` exige `initial_record_number`.
- Criação válida produz `Patient` e `PatientRecordNumber` consistentes.
- Rollback transacional é comprovado por teste.
- Nenhum arquivo fora do escopo foi alterado.

## Handoff da slice

Ao terminar, reporte:

- arquivos alterados;
- testes executados e resultado;
- qualquer falha/blocker;
- confirmação de que não iniciou a próxima slice.
