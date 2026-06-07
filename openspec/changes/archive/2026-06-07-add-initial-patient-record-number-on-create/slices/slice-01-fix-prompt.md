# Slice 01 Fix Prompt - Ajustes antes do Slice 02

Implemente **somente** estes ajustes de correção/limpeza do Slice 01.
Você ainda está no contexto do Slice 01; não inicie o Slice 02.

## Objetivo

Corrigir observações do avaliador e deixar a suíte focada de formulários verde antes de seguir para UI.

## Arquivos permitidos

- `apps/patients/forms.py`
- `apps/patients/tests/test_forms.py`

Não toque em views, templates, URLs, models ou outros testes nesta correção.

## Ajustes obrigatórios

### 1. Tornar `is_current` explícito

Em `PatientForm.save()`, na criação de `PatientRecordNumber`, passe explicitamente:

```python
is_current=True,
```

Motivo: hoje funciona pelo default do model, mas a intenção de negócio deve ficar explícita.

### 2. Simplificar teste de criação do record number

Corrija `test_patient_form_save_creates_patient_record_number` para usar o fluxo normal:

1. criar `PatientForm` válido;
2. setar `form.instance.created_by` e `form.instance.updated_by`;
3. setar `form.current_user`;
4. chamar apenas `form.save(commit=True)`;
5. verificar que existe exatamente um `PatientRecordNumber` atual.

Remova o fluxo confuso `save(commit=False) -> patient.save() manual -> save(commit=True)`.

### 3. Corrigir teste antigo sem tags

Em `test_patient_form_save_without_tags`, não use `patient.tags`, pois esse atributo não existe mais no modelo atual.

Use a relação atual:

```python
patient.patient_tags.count()
```

ou remova o assert de contagem se ele não for essencial para o objetivo do teste.

### 4. Corrigir testes antigos de status forms

Atualize os testes válidos para refletirem os campos obrigatórios atuais:

- `test_admit_patient_form_valid` deve enviar também:
  - `admission_datetime`
  - `admission_type`
  - `ward`
- `test_discharge_patient_form_valid` deve enviar também:
  - `discharge_datetime`
  - `discharge_type`
  - `discharge_reason`

Use valores válidos e não futuros. Pode usar `timezone.now().strftime(...)` em formato compatível com o input `datetime-local`.

## Critérios de aceite

- `PatientRecordNumber.objects.create(...)` recebe `is_current=True` explicitamente.
- O teste de criação do record number representa o fluxo real de `form.save(commit=True)`.
- `test_patient_form_save_without_tags` não acessa atributo inexistente.
- `test_admit_patient_form_valid` passa.
- `test_discharge_patient_form_valid` passa.
- Nenhum arquivo fora dos permitidos é alterado.

## Verificação obrigatória

Execute:

```bash
./scripts/test.sh apps.patients.tests.test_forms
```

Se passar, opcionalmente execute também:

```bash
./scripts/test.sh apps.patients.tests.test_forms.PatientFormTests
```

## Handoff esperado

Reporte:

- arquivos alterados;
- testes executados e resultado;
- confirmação de que não iniciou o Slice 02;
- qualquer blocker remanescente.
