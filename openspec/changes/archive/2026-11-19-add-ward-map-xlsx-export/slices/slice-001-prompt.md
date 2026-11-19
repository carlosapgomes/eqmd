# Slice 001 Prompt — Serviço de workbook XLSX

Implemente **somente** a slice WMX-S1 da change `add-ward-map-xlsx-export`.
Comece com contexto zero e leia os arquivos na ordem indicada.

## Pre-read obrigatório

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `openspec/changes/add-ward-map-xlsx-export/proposal.md`
4. `openspec/changes/add-ward-map-xlsx-export/design.md`
5. `openspec/changes/add-ward-map-xlsx-export/specs/patient-map-export/spec.md`
6. `openspec/changes/add-ward-map-xlsx-export/slices/slice-001-export-workbook-service.md`

## Objetivo

Criar o serviço puro que transforma os rows já resolvidos do mapa
(`ward_data`) em um workbook XLSX: uma aba por ala sobrevivente, colunas
fixas `Leito`, `Identificação`, `Médico/Interno`, `Evolução`, `Conduta`,
larguras fixas 12/48/32/72/45, bloco de identificação rotulado e a última
evolução publicada (rascunhos excluídos).

## Arquivos permitidos

- `apps/patients/services/ward_map_export.py` (novo)
- `apps/patients/tests/test_ward_map_export.py` (novo)

Nenhum outro arquivo pode ser criado ou alterado nesta slice. Não toque em
views, URLs ou templates.

## TDD obrigatório

Escreva os testes antes da implementação. Cobertura mínima exigida pelo
contrato da slice:

- uma aba por ala sobrevivente, na ordem do mapa; ala retida vazia
  (`show_empty_wards`) gera aba só com cabeçalho;
- cinco colunas na ordem contratada; `Conduta` sempre vazia;
- bloco `Identificação`: seis linhas rotuladas, datas `DD/MM/AAAA`, dias
  calculados com o `today` injetado, valores em branco quando ausentes e
  linha de Internação omitida sem data de admissão;
- evolução: mais recente publicada vence (desempate `-created_at` e, em
  empate total, `-pk`); rascunhos (humanos e de bot) e deletadas excluídos;
  sem evolução → autor e conteúdo vazios;
- autor via `get_full_name()` com fallback `username`;
- título de aba: caracteres proibidos removidos, limite de 31, fallback
  para nome sanitizado, base determinística `Ala` quando ambos ficarem
  vazios, dedupe numérico case-insensitive (incluindo títulos com sufixo);
- segurança de texto: valores com prefixo de fórmula (ex.: `=`) são
  gravados como texto literal (data type string explícito) e caracteres de
  controle XML-ilegais são removidos de todo valor exportado (round-trip
  com nota iniciando em `=`, leito com cara de fórmula e nota com caractere
  de controle);
- row descartada: paciente soft-deletado durante o TTL do cache (ausente na
  query de identidade) é omitido por completo — identificação e evolução
  incluídas — e o build nunca falha; alta dentro da janela NÃO descarta
  (o paciente segue existindo no banco);
- larguras fixas conforme constantes;
- truncagem do conteúdo a 32.767 caracteres;
- no máximo duas queries de enriquecimento em lote (`assertNumQueries` no
  teste representativo com resultado não vazio; conjunto vazio não exige
  query).

## Regras de implementação

- Constantes nomeadas para colunas, larguras e limites (sem números
  mágicos); funções com no máximo 25 linhas.
- Evolução: uma única query PostgreSQL `DISTINCT ON` com
  `select_related("created_by")` e desempate final `-pk`; use apenas o
  manager default de `DailyNote` (ele já exclui rascunhos e deletadas).
- Estilo de cabeçalho igual ao precedente de `apps/research/views.py`
  (negrito, branco, fundo #366092, centralizado).
- Não reimplemente filtros, permissões ou leitura de cache: a slice
  consome os rows prontos.

## Verificação obrigatória

```bash
./scripts/test.sh apps.patients.tests.test_ward_map_export
```

## Critérios de aceite

- Todos os testes da slice passam (RED → GREEN comprovado).
- Nenhum arquivo fora da lista permitida foi alterado.
- Sem duplicação de lógica existente e sem refatorações não relacionadas.

## Handoff da slice

Ao terminar, escreva `/tmp/eqmd-ward-map-xlsx-export/WMX-S1-report.md` com
`READY_FOR_REVIEW` ou `BLOCKED_NEEDS_DECISION`, mapeamento
requisito-evidência, arquivos alterados, prova RED/GREEN e comandos com
status de saída. Reporte e **pare** — não inicie a próxima slice.

## Guardrails

- Nunca execute comandos destrutivos (`rm -rf`, `git reset --hard`, drops
  de banco) sem aprovação explícita.
- Use `docker exec eqmd_dev` para python/pip/manage.py e
  `./scripts/test.sh` para verificação.
- Sem commits de Git.
- Se faltar informação, PARE e pergunte (BLOCKED_NEEDS_DECISION).
