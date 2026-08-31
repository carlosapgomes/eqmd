# Design: Patient Identity and Duplicate Prevention

## Context

`PatientForm.save()` cria `Patient` e `PatientRecordNumber`, enquanto
`Patient.update_current_record_number()` troca o prontuário atual. Os forms e
as views validam formato, mas não consultam todo o histórico nem possuem uma
constraint global. A constraint atual `unique_current_record_per_patient`
garante somente um prontuário atual por paciente.

`Patient`, `PatientRecordNumber`, forms e views estão em arquivos brownfield
acima do limite de tamanho atual. Nova lógica de identidade deve ficar em um
serviço coeso; integrações nesses arquivos devem ser curtas e não iniciar um
refactor amplo dentro desta feature.

A auditoria agregada encontrou:

- 37 grupos de prontuário compartilhados por pacientes distintos;
- 79 pacientes afetados no histórico;
- 33 grupos e 72 pacientes afetados entre prontuários atuais;
- 3 repetições do mesmo prontuário no histórico do mesmo paciente;
- 228 grupos, 469 pacientes e 255 pares com nome normalizado e nascimento
  iguais;
- 27 pares adicionais com mesmo nascimento e similaridade de nome maior ou
  igual a 0,70;
- 8 CNS de 15 dígitos duplicados, afetando 16 pacientes;
- nenhum paciente excluído logicamente na cópia auditada.

As extensões PostgreSQL `pg_trgm` e `unaccent` já existem. A aplicação usa
PostgreSQL exclusivamente.

## Goals / Non-Goals

**Goals:**

1. Avisar sobre nome igual ou semelhante com mesmo nascimento sem transformar
   essa combinação em unicidade.
2. Bloquear conflito por CPF/CNS somente quando o identificador fornecido for
   válido, normalizado e não vazio.
3. Impedir que um prontuário atual ou histórico seja atribuído novamente,
   inclusive ao mesmo paciente ou após soft delete.
4. Fechar a janela de concorrência de prontuário no PostgreSQL.
5. Retornar erros de domínio no formulário sem deixar paciente ou prontuário
   parcial.
6. Manter a implementação pequena, tipada e verificável por slices verticais.

**Non-Goals:**

- Consolidar, excluir, fundir ou escolher automaticamente pacientes existentes.
- Corrigir em massa os 37 grupos de prontuário ou os CNS legados.
- Criar um algoritmo probabilístico que decida identidade clínica.
- Tornar nome+nascimento, CPF ou CNS constraints de unicidade neste change.
- Reescrever integralmente `models.py`, `forms.py`, `views.py` ou `signals.py`.
- Alterar permissões, soft delete, importadores históricos ou APIs públicas sem
  requisito explícito.
- Criar ADR fora de `openspec/`; a decisão pode ser promovida a ADR em trabalho
  de governança posterior.

## Decisions

### 1. Política de identidade em três níveis

- Prontuário: invariante forte e global. Uma atribuição persistida fica
  reservada para sempre e não pode ser reativada nem transferida.
- CPF/CNS: evidência forte somente se o valor novo for válido e coincidir com
  outro paciente. O fluxo interativo bloqueia a gravação conflitante.
- Nome+nascimento: evidência consultiva. O usuário deve revisar e confirmar,
  mas pode continuar quando não houver conflito forte.

Não será usada uma constraint de nome+nascimento porque homônimos são válidos.
CPF e CNS não recebem constraint neste change devido à baixa cobertura e às
inconsistências legadas; essa decisão evita uma limpeza implícita de dados.

### 2. Serviço dedicado de identidade

Criar `apps/patients/services/patient_identity.py` para:

- normalizar nome e documentos;
- retornar DTOs mínimos de candidatos;
- executar a consulta de similaridade;
- classificar evidência consultiva e forte;
- consultar conflitos de prontuário para os fluxos de aplicação.

O serviço não cria, funde nem exclui pacientes. Forms coordenam validação de
entrada e views continuam responsáveis apenas por transporte, mensagens e
redirecionamento. Mudanças em arquivos legados devem delegar ao serviço.

Alternativa rejeitada: colocar consultas e limiares diretamente em forms ou
views. Isso duplicaria lógica entre criação, atualização e prontuário rápido.

### 3. Busca por nome filtrada primeiro por nascimento

A busca consultiva usa a mesma data de nascimento e compara nomes após
normalização de caixa, acentos, pontuação e espaços. Nomes exatos sempre são
candidatos; nomes diferentes entram quando a similaridade `pg_trgm` for maior
ou igual a **0,80**.

O limiar foi escolhido após a auditoria: havia 6 pares em 0,90, 19 em 0,80 e
27 em 0,70. O filtro de nascimento reduz custo e falsos positivos. O serviço
consulta também `Patient.all_objects` para não recriar paciente em soft delete.

Alternativa rejeitada: busca global sem nascimento. Ela aumentaria ruído e
exposição desnecessária de dados identificáveis.

### 4. Revisão em dois passos, sempre revalidada no servidor

No primeiro POST com candidatos apenas consultivos, nenhum paciente é criado.
O mesmo formulário mostra alerta e dados mínimos dos candidatos. O usuário
pode reenviar com confirmação explícita. O segundo POST executa novamente a
busca; a confirmação não é um bypass para conflito forte nem para prontuário
reservado.

O painel pode mostrar nome, nascimento, prontuário atual, estado ativo/excluído
e badges do tipo de evidência. Não mostra CPF, CNS, endereço ou telefone.
Permissões e CSRF existentes são preservados.

Alternativa rejeitada: confirmação apenas em JavaScript. Ela seria burlável e
não protegeria submissões diretas.

### 5. CPF e CNS canônicos apenas quando novos ou alterados

CPF é normalizado para 11 dígitos e validado pelos dois dígitos verificadores.
CNS é normalizado para 15 dígitos e validado pela soma ponderada oficial. Valor
vazio continua permitido.

Na edição, um valor legado inválido e não alterado não bloqueia mudanças em
outros campos. Um identificador novo ou alterado precisa ser válido. A busca
forte exclui o próprio paciente no update.

A interface passa a usar “CNS” e “Cartão Nacional de Saúde”; menções a
carteira de plano de saúde são removidas dos dois formulários de paciente.

### 6. Defesa de prontuário em aplicação e banco

A chave canônica de prontuário ignora espaços externos e caixa das letras. A
aplicação consulta todo `PatientRecordNumber`, sem filtrar atualidade ou soft
delete, antes de criar ou trocar uma atribuição.

A troca é atômica: validar/reservar, desativar o atual, criar o novo e atualizar
o campo denormalizado. Se qualquer passo falhar, o prontuário anterior continua
atual.

A garantia autoritativa será uma `UniqueConstraint` funcional PostgreSQL sobre
`Lower(Trim(record_number))`. Ela bloqueia também concorrência, importadores e
ORM direto. A aplicação converte a violação conhecida em erro de domínio nos
fluxos interativos.

Atribuições persistidas não podem mudar de número nem ser removidas pelos
fluxos ordinários ou pelo admin. Correções de dados exigem procedimento de
consolidação separado e auditável.

Alternativas rejeitadas:

- somente `form.clean()`: possui janela de corrida;
- somente signal: não protege `bulk_create` e é difícil de raciocinar;
- reutilizar `unique_current_record_per_patient`: ela tem escopo por paciente,
  não por número;
- normalizar todos os dados automaticamente: as colisões exigem decisão humana.

### 7. Migration falha de forma segura diante do legado

A migration nova executa um preflight somente leitura antes de adicionar a
constraint. Se houver chaves canônicas repetidas, ela aborta antes da alteração
de schema e informa apenas contagens agregadas, nunca números de prontuário ou
identificadores de pacientes.

Ela não altera registros, não escolhe vencedor e não remove linhas. O change de
consolidação deve zerar conflitos antes do rollout final.

### 8. Dimensionamento em quatro slices verticais

1. Aviso por nome+nascimento, com confirmação end-to-end.
2. Bloqueio por CPF/CNS válido e terminologia CNS.
3. Proteção dos fluxos de prontuário e imutabilidade do histórico.
4. Constraint concorrente e preflight de migration.

Três slices tornariam o terceiro grande demais para DeepSeek4-Flash; cinco ou
mais separariam testes, UI ou banco em fatias horizontais sem valor autônomo.

## Risks / Trade-offs

- **Baseline atualmente vermelho** → nenhum implementador pode editar antes de
  `./scripts/test.sh` retornar zero failures/errors.
- **`ruff` ausente no container auditado** → provisionar o toolchain fora dos
  slices; é proibido instalar pacotes ad hoc durante um slice.
- **Constraint incompatível com dados atuais** → preflight fail-closed e rollout
  condicionado ao change separado de consolidação.
- **Homônimo tratado como duplicata** → correspondência de nome é somente aviso
  com confirmação explícita.
- **Identificador legado inválido impede edição** → valores inválidos e
  inalterados são preservados; somente valor novo/alterado é validado.
- **Resultado de busca expõe PII** → DTO e template exibem apenas o mínimo e
  nunca mostram CPF/CNS brutos.
- **Arquivos legados muito grandes** → nova lógica fica no serviço; integrações
  devem ser pequenas e o relatório deve registrar linhas antes/depois.
- **Constraints de CPF/CNS ausentes** → risco residual em gravações fora do
  fluxo interativo é aceito até um futuro change de saneamento de documentos.

## Migration Plan

1. Restaurar baseline verde e disponibilizar `ruff`/`mypy` no container.
2. Implementar e verificar slices 1 a 3, um por vez.
3. Abrir e executar change separado de consolidação auditável.
4. Confirmar em relatório agregado:
   - zero prontuários canônicos entre pacientes distintos;
   - zero prontuários canônicos repetidos no mesmo paciente.
5. Implementar/verificar o slice 4 em banco de teste PostgreSQL limpo.
6. Aplicar migration em staging com backup e repetir a auditoria agregada.
7. Aplicar em produção somente após aprovação clínica/operacional.

Rollback de aplicação: reverter integrações de forms/template/views preservando
os dados criados. Rollback da migration: remover apenas a constraint; não há
migration reversa que altere ou exclua dados. Nunca executar drop, truncate ou
reset de banco como parte destes slices.

## Open Questions

Não há questão funcional aberta para implementação. O rollout final permanece
bloqueado até o change separado resolver as colisões agregadas conhecidas.
