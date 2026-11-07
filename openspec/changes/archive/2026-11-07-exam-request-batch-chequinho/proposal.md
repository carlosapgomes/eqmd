# Proposal: exam request batch (chequinho)

## Why

Solicitar vários exames SUS ("chequinho") para o mesmo paciente exige hoje um
fluxo completo por exame: abrir o formulário genérico, redigitar a mesma
justificativa, salvar e imprimir uma folha A4 por exame — mesmo o formulário
ocupando só o terço superior da página. Os usuários já usam a duplicação como
workaround (a submission mais recente do template é uma duplicata), mas isso
ainda custa N page-loads e N impressões com 2/3 de papel desperdiçado.

## What Changes

- Nova página dedicada de solicitação de exames em lote para o template
  "Solicitação de Exames SUS" (estilo APAC): campos compartilhados (motivo,
  data, médico, com os auto-fills atuais) + formset dinâmico de 1–N exames
  (texto livre + código opcional, como hoje).
- POST cria N `PDFFormSubmission` (1 por exame) em transação, todas com o
  mesmo `batch_id` dentro de `form_data`, reaproveitando o overlay e as
  coordenadas já configurados — sem mudar o motor genérico.
- Nova view de download do lote que compõe até **3 vias por folha A4**
  (preencher → recortar no bbox fixo → empilhar 1:1, com linha de corte
  tracejada só entre vias impressas). Vias idênticas ao avulso.
- Paginação `ceil(N/3)`: qualquer N (2, 4, 9…) imprime corretamente, com a
  última folha parcialmente preenchida.

## Impact

- Affected specs: pdf-forms
- Affected code: apps/pdf_forms/views/ (nova view de lote + view de download),
  apps/pdf_forms/services/ (novo módulo de imposição N-up), templates
  pdf_forms/ (página de lote), urls.py, tests em apps/pdf_forms/tests
- Uses existing: PDFFormTemplate `dde2a393` (overlay/coordenadas), PDFFormOverlay,
  pypdf + reportlab (já dependências), supervisão draft/final existente
- Non-goals: grupos repetíveis no motor genérico, busca MedicalProcedure
  (fase 2), redesenho do PDF oficial, bbox configurável no admin
