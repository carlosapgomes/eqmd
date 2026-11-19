# Slice 003 Prompt — Botão Exportar xlsx no mapa

Implemente **somente** a slice WMX-S3 da change `add-ward-map-xlsx-export`.
Comece com contexto zero e leia os arquivos na ordem indicada.

## Pre-read obrigatório

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `openspec/changes/add-ward-map-xlsx-export/proposal.md`
4. `openspec/changes/add-ward-map-xlsx-export/design.md` (seção D4)
5. `openspec/changes/add-ward-map-xlsx-export/specs/patient-map-export/spec.md`
6. `openspec/changes/add-ward-map-xlsx-export/slices/slice-003-export-button-ui.md`
7. O endpoint entregue em WMX-S2:
   `apps/patients/views_ward_map_export.py`

## Objetivo

Exibir o botão `Exportar xlsx` na página do mapa, **acima do card de
resultados** e **fora do formulário de filtros**, com dois estados
server-rendered (sem JavaScript): habilitado (com a querystring corrente)
quando há pacientes no resultado; desabilitado quando o resultado está
vazio.

## Arquivos permitidos

- `apps/patients/templates/patients/ward_patient_map.html`
- `apps/patients/tests/test_ward_map_export_view.py` (apenas estender com
  os casos de UI, reutilizando os fixtures existentes)

Nenhum outro arquivo pode ser criado ou alterado. Nenhum JavaScript, asset
ou build.

## TDD obrigatório

Escreva os testes antes do markup. Cobertura mínima exigida:

- a linha de ação renderiza acima do card de resultados e **fora** do
  `<form method="get">` e do painel `data-patient-filter-panel`;
- com pacientes no resultado: âncora com
  `href="{% url 'patients:patient_map_export' %}"` + querystring corrente
  (com `?q=` e `?ward=` presentes na request); sem parâmetros, sem `?`
  sobrando no href; parâmetros repetidos (ex.: `tags=...&tags=...`) são
  preservados no href;
- com resultado vazio (filtros sem match, cache vencido **ou** zero
  pacientes com `show_empty_wards=true` retendo alas vazias): âncora sem
  `href`, classe `disabled`, `aria-disabled="true"`, `tabindex="-1"` e
  `title` explicativo; a linha de exportação decide apenas por
  `total_patients` (nunca referencia `updating`);
- o botão **não** renderiza no partial AJAX
  (`ward_patient_map_tree_only.html`);
- suíte completa passa (`./scripts/test.sh`) sem regressão no mapa.

## Regras de implementação

- Uma única linha/row nova no template, entre o alerta de `updating` e a
  seção "Tree View Section"; nada mais no template muda (filtros, opções de
  visualização, painel de preferência e árvore ficam intocados).
- Estados por `{% if total_patients %}` ... `{% else %}` ... `{% endif %}`,
  decididos no servidor; nenhuma alteração em views ou JS.
- Reuse classes já existentes do projeto (por exemplo
  `btn-medical-outline-primary` e o ícone `bi-file-earmark-excel`).
- Âncora desabilitada correta: sem `href`, `aria-disabled="true"`,
  `tabindex="-1"`, `title="Nenhum paciente no resultado da busca"`.

## Verificação obrigatória

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_export_view
./scripts/test.sh
```

## Critérios de aceite

- Todos os testes da slice passam (RED → GREEN comprovado).
- Posição e estados do botão conformes ao spec delta.
- Partial AJAX inalterado e sem botão.
- Suíte completa verde; nenhum arquivo fora da lista permitida alterado.

## Handoff da slice

Ao terminar, escreva `/tmp/eqmd-ward-map-xlsx-export/WMX-S3-report.md` com
`READY_FOR_REVIEW` ou `BLOCKED_NEEDS_DECISION`, mapeamento
requisito-evidência, arquivos alterados, prova RED/GREEN, comandos com
status de saída e o resumo da suíte completa. Reporte e **pare**.

## Guardrails

- Nunca execute comandos destrutivos (`rm -rf`, `git reset --hard`, drops
  de banco) sem aprovação explícita.
- Use `docker exec eqmd_dev` para python/pip/manage.py e
  `./scripts/test.sh` para verificação.
- Sem commits de Git; não atualize `tasks.md`.
- Se for preciso mudar o formulário, o contrato AJAX ou qualquer arquivo
  fora da lista, PARE e reporte (BLOCKED_NEEDS_DECISION).
