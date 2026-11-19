# Slice 002 Prompt — Endpoint de exportação

Implemente **somente** a slice WMX-S2 da change `add-ward-map-xlsx-export`.
Comece com contexto zero e leia os arquivos na ordem indicada.

## Pre-read obrigatório

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `openspec/changes/add-ward-map-xlsx-export/proposal.md`
4. `openspec/changes/add-ward-map-xlsx-export/design.md`
5. `openspec/changes/add-ward-map-xlsx-export/specs/patient-map-export/spec.md`
6. `openspec/changes/add-ward-map-xlsx-export/slices/slice-002-export-endpoint.md`
7. O serviço entregue em WMX-S1:
   `apps/patients/services/ward_map_export.py`

## Objetivo

Criar o endpoint nomeado que exporta o resultado atual da busca do mapa
como download XLSX: herda `WardMapFilterActionsView`, resolve o contexto uma
única vez, recusa resultado vazio (409 + mensagem, sem arquivo) e responde
com `Content-Disposition: attachment` e filename
`mapa_pacientes_YYYYMMDD_HHMMSS.xlsx`.

## Arquivos permitidos

- `apps/patients/views_ward_map_export.py` (novo)
- `apps/patients/urls.py` (somente adicionar a rota
  `path("map/export/", ...)` com name `patient_map_export`, ao lado da
  rota `map/`)
- `apps/patients/tests/test_ward_map_export_view.py` (novo)

Nenhum outro arquivo pode ser criado ou alterado. Não toque em templates
nem na view do mapa.

## TDD obrigatório

Escreva os testes antes da implementação. Cobertura mínima exigida:

- anônimo → redirect para login; autenticado sem
  `patients.view_patient` → 403;
- cache quente com pacientes → 200, content-type XLSX oficial,
  `Content-Disposition: attachment` com filename no padrão esperado, e
  corpo que abre como workbook válido (`load_workbook`);
- paridade com a busca: com `?q=`, `?ward=` e `?tag_filter` (incluindo
  uma variante com parâmetros repetidos), os pacientes exportados são
  exatamente os rows que a view do mapa renderiza nas mesmas condições;
- resultado vazio (filtros sem match, cache vencido/ausente **ou** zero
  pacientes com `show_empty_wards=true` retendo alas vazias) → 409,
  mensagem em texto, sem header de attachment;
- request com header AJAX (`X-Requested-With`) ainda recebe o arquivo (a
  view não usa o branch de partial do mapa).

## Regras de implementação

- `WardMapExportXlsxView(WardMapFilterActionsView)` sobrescreve somente
  `get()`; chama `get_context_data()` uma única vez; nunca re-resolve
  preferências nem lê o cache diretamente.
- View fina: sem lógica de workbook (consuma o serviço de WMX-S1); sem
  números mágicos; funções curtas.
- Recusa única: `total_patients == 0` → 409 + mensagem explicativa em texto
  simples. Nenhum critério extra (nem para `updating`).

## Verificação obrigatória

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_export_view \
  apps.patients.tests.test_ward_map_export
```

## Critérios de aceite

- Todos os testes da slice passam (RED → GREEN comprovado).
- Gates de permissão herdados comprovados por teste.
- Paridade export = resultado renderizado comprovada por filtro.
- Nenhum arquivo fora da lista permitida foi alterado.

## Handoff da slice

Ao terminar, escreva `/tmp/eqmd-ward-map-xlsx-export/WMX-S2-report.md` com
`READY_FOR_REVIEW` ou `BLOCKED_NEEDS_DECISION`, mapeamento
requisito-evidência, arquivos alterados, prova RED/GREEN e comandos com
status de saída. Reporte e **pare** — não inicie a próxima slice.

## Guardrails

- Nunca execute comandos destrutivos (`rm -rf`, `git reset --hard`, drops
  de banco) sem aprovação explícita.
- Use `docker exec eqmd_dev` para python/pip/manage.py e
  `./scripts/test.sh` para verificação.
- Sem commits de Git.
- Se faltar informação ou se for preciso alterar a view do mapa ou o
  contrato de contexto, PARE e reporte (BLOCKED_NEEDS_DECISION).
