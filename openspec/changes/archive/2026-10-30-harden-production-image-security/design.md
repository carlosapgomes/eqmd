# Design: correção delimitada da imagem produtiva

## Context

Ver `proposal.md` e `evidence/baseline.json`. A imagem de referência é
`7087e3e...`, revisão `6e2928c`, não o `latest` publicado pelo CI corrigido.
O runtime instalado foi confirmado por extração estática de METADATA; caches
`uv` na imagem não foram tratados como prova de pacote inativo.

O Dockerfile atual instala dependências pelo lock, mas copia o contexto inteiro,
não exclui genericamente `temp/`/secrets e deixa cache de instalação no runtime.
O diretório local de evidências já contém gigabytes; não construir esse contexto
sem corrigir primeiro as exclusões. O Compose dev inicia `migrate` por padrão.

## Goals / Non-Goals

Objetivo: candidato local auditável, com os cinco alvos corrigidos e contratos
preservados. Não há deploy, domínio novo, upgrade de banco, mudança de schema,
separação de workers ou nova política de autenticação neste change.

A estratégia proposta está registrada em
`docs/adr/ADR-0004-bounded-production-image-security-remediation.md`, Proposed.

## Decisions

### D1. Atualização seletiva, não refresh global

Pisos aprovados para planejamento:

- Django `>=5.2.17,<5.3`.
- Django REST framework `>=3.18.2,<3.19`.
- certifi `>=2026.10.18`, versão concreta resolvida no lock.
- Pillow `>=13.0.0,<14`.
- Brotli Debian 13: versão instalada comparável por dpkg, no mínimo
  `1.1.0-2+deb13u1`.

Promover DRF/certifi a dependências explícitas se hoje forem apenas transitivas:
a aplicação usa DRF diretamente e o piso TLS deve sobreviver à resolução.
Modificar `uv.lock` seletivamente pelos alvos; explicar cada transiente alterado.
Não permitir upgrade intencional de pypdf, PyJWT, AnyIO ou outras famílias.
Se o resolver exigir mudança material fora desse envelope, bloquear e revisar,
sem aceitar a resolução ampla como efeito colateral inevitável.

Alternativas rejeitadas: `uv lock --upgrade` global, `pip install -U` no runtime,
usar `latest` como correção, ou pin antigo apenas para reduzir o diff.

### D2. Rebuild seguro antes de qualquer atualização Python

A família S1 altera apenas construção/contexto e seus testes. S1a primeiro
comprova a fronteira do contexto em fixture isolada; somente após seu aceite
S1b altera base/cache/Brotli e constrói o runtime do projeto:

- Base Python continua 3.12/Debian 13, preferindo nome de distribuição explícito
  e digest selecionado/documentado pelo implementador.
- APT precisa fornecer Brotli corrigido. Usar comparação de versões dpkg,
  não comparação lexical. Repositório ausente ou versão insuficiente bloqueia.
- Não usar Debian testing, compilar patch manual ou trocar distribuição para
  contornar um advisory sem nova decisão.
- Cache `uv` deve ser não persistente no runtime por mecanismo suportado de
  build. Não limpar caches do host/volumes como atalho.
- Excluir secrets `.env*`, chaves/configurações privadas, backups, logs, mídia
  local e `temp/` do contexto. Preservar arquivos não secretos realmente usados
  pelos targets existentes; não quebrar Dockerfile.synapse por exclusão ampla
  de módulos de código, mesmo que Synapse não seja ativado nesta migração.
- Não inventar uma allowlist de extensões que remova bibliotecas ou fixtures
  necessárias sem validar os targets.

O teste de contexto usa somente fixtures sintéticas com nomes de secrets e
reproduz a semântica do Docker/build real em um contexto isolado. Nunca enviar
`.env` real para provar depois que ele não deveria estar lá.

APT online não é bit-a-bit reproduzível por fixar somente a imagem base.
Registrar digest de base, instante de build e manifesto dpkg do candidato;
o contrato é lock Python reproduzível e composição nativa auditável, não uma
promessa falsa de snapshot imutável de todo repositório APT.

### D3. Três famílias, cinco contratos executáveis

A revisão de dimensionamento está em `slice-review.md`. As decisões técnicas
não mudaram; separaram-se entregas com provas e modos de falha independentes:

1. S1a: fronteira de contexto comprovada por build isolado com sentinelas.
2. S1b: candidato nativo com Brotli/cache corrigidos, sem alterar lock Python.
3. S2: Django/DRF/certifi e contratos HTTP/OIDC; permanece uma unidade porque
   a resolução e a validação de framework/DRF são acopladas.
4. S3a: Pillow 13 com toda a regressão de mídia/PDF/vídeo e candidato identificado.
5. S3b: qualificação do mesmo artefato por comparação de scans e dossiê residual,
   sem alterar código/dependências para consertar falhas descobertas.

S1a não precisa de rebuild nativo; S1b não resolve contexto ainda inseguro.
S3a não deixa seus testes para S3b. S3b entrega verificação end-to-end de
segurança, não um slice artificial só de documentação. Os índices `group-*`
são mapas das famílias, não contratos executáveis adicionais.

Cada unidade termina com os gates pertinentes e revisão; não há passagem
automática. A suíte é devida em cada unidade que altera código/build; S3b
confere a evidência do mesmo artefato e renova os gates se houver rebuild.
Mudança de compatibilidade só pode preservar contrato e precisa de teste
antes/depois e caminhos autorizados pelo slice. Nenhum intermediário é
promovido implicitamente a candidato aceito para deploy.

### D4. Ambiente de teste não pode continuar com dependências antigas

Todas as operações Python/uv/manage.py continuam dentro de `eqmd_dev`.
Não instalar pacotes no host nem mutar o runtime em execução para obter verde;
seguir ADR-0001, reconstruindo a imagem dev a partir do lock quando autorizado.
Uma suite verde em Django antigo após editar o lock não prova a correção.

Antes de recriar `eqmd_dev`, apresentar ao operador o plano exato e obter
aprovação local. Não executar `compose up` cegamente: o startup atual dispara
`migrate`. Recriação deve evitar migrations automáticas e manter dados dev
preservados; usar configuração operacional temporária aprovada, sem alterar
Compose produtivo. Sem autorização/ambiente atualizado, retornar bloqueio.

Registrar versões via METADATA/importlib e compará-las exatamente ao lock,
para todos os alvos já introduzidos. O gate legado que compara só minor do
Django não basta. Tests/manage.py não podem rodar na origem/Eon nem usar
SQLite ou dados clínicos. Qualquer banco de ensaio é PostgreSQL sintético e
sua criação precisa da autorização operacional correspondente.

### D5. Imagem, scan e comparação são evidência do mesmo artefato

S3a entrega candidato identificado; S3b confere a identidade imutável
local/OCI e o manifesto da imagem final,
plataforma, base e versões instaladas. Antes de publicação não inventar um
RepoDigest GHCR inexistente: image ID/config digest e manifest digest são
identidades diferentes e precisam ser rotulados corretamente.

Scan local pode usar a imagem pelo daemon sem executá-la, ou exportação OCI,
em scanner aprovado com base válida. Não montar socket Docker sem justificar
seu privilégio; preferir arquivo de imagem/registry quando aplicável. Build,
scanner/containers descartáveis e recriações exigem aprovação para comandos
locais exatos; isso nunca autoriza acessar produção.

Comparar baseline e candidato com a mesma versão de scanner, política e snapshot
de base válido, ou reanalisar ambos com a mesma base atualizada. Não desligar
validação de idade/hash, filtrar `only-fixed` ou adicionar ignores/VEX de conveniência.
Preservar o conjunto final `squashed` e relatar supressões padrão separadamente.

A baseline portátil contém advisories dos cinco alvos. O aceite exige versões
instaladas corrigidas e ausência de matches afetados desses alvos, inclusive
novos avisos conhecidos na data da validação. Repositório/ABI indisponível,
novo advisory prioritário ou patch insuficiente exige revisão, não sucesso
por bater um número histórico de CVEs removidos.

### D6. Risco residual continua uma decisão humana

O objetivo não é zero CVEs. Pypdf, PyJWT, AnyIO, FFmpeg/Poppler e demais itens
fora do alvo precisam aparecer na comparação residual, com mudanças de pacote,
severidade, correção, pré-condições e controles observáveis.

Worker pode produzir candidato pronto para revisão. Não pode aceitar residual,
substituir baseline produtiva nem autorizar a migração. Qualquer exceção precisa
de responsável, justificativa, prazo e aceite explícito do operador. Nenhuma
exceção existe por ter sido usado `fail-build: false` no CI.

## Risks / Trade-offs

- Pillow major → testes reais de JPEG/PNG/WebP, thumbnails e formulários, sem
  usar exploit destrutivo ou conteúdo clínico.
- Django/DRF podem revelar drift OIDC → check/makemigrations não mutantes;
  preservar AutoField e parar se houver migration/vendor incompatível.
- Versões PyPI não garantem ABI → resolver e testar wheels/build em Python 3.12.
- APT atualiza outros pacotes → manifesto dpkg antes/depois e rescan; nenhuma
  dependência nova sem justificativa.
- Dependência fora do alvo muda para satisfazer resolver → revisão de blast
  radius antes de aceitar; não esconder em lockfile extenso.
- Excluir somente cache pode reduzir contagem sem corrigir pacote → confirmar
  versões instaladas; não aceitar queda numérica como evidência suficiente.
- Substituir artefato altera rollback → conservar imagem anterior e não aceitar
  migrations/escritas produtivas neste change.

## Migration Plan

Não há implantação autorizada. A sequência local é S1a → revisão → S1b →
revisão → S2 → revisão → S3a → revisão → S3b → revisão de segurança → decisão
explícita do operador sobre artefato. Os cinco contratos ativos estão em
`slices/slice-*.md` e permanecem não iniciados. Não executar uma família
inteira sob autorização dada somente para uma das suas unidades.

Publicar no GHCR, selecionar versão de release e consumir candidato no plano
de migração são etapas posteriores autorizadas pelo operador. Nenhum push/tag
ou script de upgrade pode ser disparado pelo implementador.

### Rollback

Reverter o slice local como unidade coerente de declaração, lock, Dockerfile e
testes associados. Não executar reset/clean destrutivo. Reconstrução/recriação
do ambiente requer autorização e deve continuar sem migration automática.
A imagem antiga continua preservada; sua vulnerabilidade não desaparece por
ser fallback. Sem alterações de schema, não há reversão de dados neste plano.
Se uma versão nova exigir schema/contrato novo, parar antes de prosseguir.

## Execution Preconditions

- Design/ADR/slice revisados e slice explicitamente autorizado.
- Ferramentas, base APT e wheels disponíveis, ou bloqueio honesto.
- Plano de build/recriação local aprovado sem tocar origem/Eon.
- Baseline portátil disponível; relatórios brutos `temp/` são contexto opcional,
  nunca dependência exclusiva para worker fresh.
- Risco residual e publicação permanecem gates humanos, não decisões ocultas.
