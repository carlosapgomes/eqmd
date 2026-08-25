# ADR-0001: Deterministic Development Quality Gates

## Status

Proposed

## Contexto

O projeto documenta Django 5.2.1, mas a dependência aberta
`django>=5.2.1` permitia upgrades fora da linha suportada. O `uv.lock` já
resolvia Django 5.2.1; o container chegou ao Django 6.1 porque o Dockerfile
instalava a partir de `pyproject.toml` sem consumir o lock. A CI usa o lock
indiretamente por `uv sync`.

A correção do runtime revelou um drift independente da versão do Django. As
migrations de `django-oidc-provider` 0.9.0 e as seis colunas preservadas no
PostgreSQL usam `AutoField`, mas o AppConfig legado do pacote herda
`BigAutoField` do projeto no estado atual dos models.

Ruff e Mypy são gates obrigatórios, porém não estão ambos provisionados de
forma reproduzível na imagem de desenvolvimento. `scripts/typecheck.sh` tenta
instalar dependências como root no container em execução quando Mypy está
ausente, contrariando o princípio de gates não mutantes.

A suíte completa também possui centenas de falhas preexistentes. Mudanças
clínicas críticas ficam bloqueadas porque não é possível distinguir com
confiança regressão nova de ruído legado.

Esta decisão integra o change OpenSpec
`restore-green-development-quality-gates`.

## Decisão

Adotar os seguintes contratos:

1. Django permanece na linha LTS 5.2, com intervalo `>=5.2.1,<5.3`, até um
   change separado aprovar upgrade de framework.
2. `uv.lock` é a fonte reproduzível de resolução para CI e imagens Docker.
3. A imagem/target de produção instala apenas dependências de runtime; a
   imagem/target de desenvolvimento instala também o grupo `dev`.
4. Ruff e Mypy são declarados no grupo `dev` com versões limitadas e ficam
   disponíveis após construção do ambiente.
5. O projeto seleciona um AppConfig de compatibilidade para
   `django-oidc-provider`, com `default_auto_field` igual a `AutoField`, até que
   uma atualização upstream ofereça um contrato de migration diferente.
6. Scripts de qualidade nunca instalam, atualizam ou executam package manager
   como root; ferramenta ausente causa falha explícita com instrução de rebuild.
7. A restauração da suíte ocorre em cohorts verticais, com contrato-first,
   target local totalmente verde e comparação da suíte completa.
8. Nenhuma mudança clínica crítica bloqueada pode prosseguir até a suíte
   completa e os gates estáticos/migrations estarem verdes.

A sintaxe concreta de instalação Docker deve ser validada contra a versão de
`uv` usada no build antes da implementação. A decisão exige consumo do lock e
separação runtime/dev, não presume um comando ainda não testado.

## Alternativas Consideradas

1. **Manter `django>=5.2.1` sem limite superior**
   - **Vantagens:** atualizações automáticas e menos manutenção manual.
   - **Desvantagens:** upgrades minor/major entram sem revisão, como ocorreu
     com Django 6.1; dependências de terceiros podem gerar drift ou quebrar.
   - **Por que não escolhida:** incompatível com runtime clínico e gates
     determinísticos.

2. **Fixar exatamente Django 5.2.1**
   - **Vantagens:** resolução totalmente previsível.
   - **Desvantagens:** impede patches de segurança/correção dentro da linha LTS
     sem editar a declaração.
   - **Por que não escolhida:** o intervalo `<5.3` permite patches compatíveis
     enquanto bloqueia upgrade de minor.

3. **Continuar instalando ferramentas sob demanda nos scripts**
   - **Vantagens:** scripts parecem autocontidos em containers incompletos.
   - **Desvantagens:** mutação como root, dependência de rede, versões variáveis
     e resultados diferentes entre execuções.
   - **Por que não escolhida:** um gate deve medir o ambiente, não modificá-lo.

4. **Aceitar baseline vermelho e comparar somente novas falhas**
   - **Vantagens:** permite avançar features imediatamente.
   - **Desvantagens:** erros reais podem permanecer ocultos; contagens mudam
     quando loaders passam a descobrir mais testes.
   - **Por que não escolhida:** aceitável apenas como transição interna dos
     slices de estabilização, nunca como gate final de feature crítica.

## Consequências

### Positivas

- Paridade verificável entre local, Docker e CI.
- Upgrades de Django passam por change dedicado e evidência explícita.
- Gates não dependem de instalação ad hoc ou estado mutável do container.
- Falhas de teste voltam a representar regressões acionáveis.
- Mudanças clínicas críticas ganham baseline confiável.

### Negativas/Trade-offs

- Alterações de dependência exigem atualização intencional do lock e rebuild.
- A imagem de desenvolvimento terá mais dependências que a de produção.
- Restaurar a suíte demanda vários slices antes de retomar novas features.
- Formatação mecânica de arquivos legados precisa ser isolada para revisão.

### Riscos e Mitigações

- **Risco:** o pin de Django revela código dependente de 6.1.
  - **Mitigação:** executar smoke, migrations e suíte após o lock antes de
    reparar cohorts; parar se houver contrato que exija 6.1.
- **Risco:** Docker runtime e dev divergem.
  - **Mitigação:** derivar targets da mesma base e verificar versões em ambos.
- **Risco:** a compatibilidade OIDC ocultar uma mudança real de schema.
  - **Mitigação:** limitar o override ao app do fornecedor, testar os seis PKs
    e CRUD sintético, e proibir migration ou alteração do default global.
- **Risco:** testes são alterados para apenas ficar verdes.
  - **Mitigação:** ordem de autoridade contract-first e revisão por terceiro
    LLM por slice.
- **Risco:** um slice cresce para múltiplos domínios.
  - **Mitigação:** stop rule e criação de follow-up quando arquivos permitidos
    forem insuficientes.

## Plano de Rollback

Reverter declaração de dependências, `uv.lock`, targets Docker, scripts e CI
como uma unidade. Rebuild/recriação de container exige aprovação do usuário.
Slices de testes são revertíveis por cohort; qualquer correção de produção deve
ser revertida junto de seu teste de regressão. Não há migration nem mutação de
dados neste ADR.

## Referências

- Change: `openspec/changes/restore-green-development-quality-gates/`
- Change precursor:
  `openspec/changes/stabilize-test-suite-lifecycle-gates/`
- Padrões: `docs/workflows/coding-standards.md`

## Histórico

- 2026-08-23: ADR criada com status Proposed.
- 2026-08-24: contexto corrigido e contrato OIDC AutoField incorporado após
  evidência do slice 001.
