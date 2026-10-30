# ADR-0004: Correção delimitada de segurança da imagem produtiva

## Status

Proposed — 2026-10-29. Planejamento autorizado; não representa execução,
aceitação de risco residual ou autorização de publicação/implantação.

## Contexto

O scan da imagem produtiva `7087e3e...` identificou 2.166 matches, incluindo
componentes instalados de Django/Pillow e Brotli presente no catálogo KEV.
A migração de host pretende preservar comportamento e PostgreSQL 15, mas usar
a mesma imagem vulnerável sem decisão explícita não é um gate de segurança.

ADR-0001 exige Django na série 5.2, resolução pelo lock e gates não mutantes.
O build atual usa `COPY . .` e não exclui genericamente evidências operacionais
e secrets locais; o diretório `temp/` não é seguro apenas por estar no Gitignore.

Change proposto:
`openspec/changes/harden-production-image-security/proposal.md`.

## Decisão proposta

1. Corrigir somente Django 5.2, DRF, Pillow, certifi e Brotli nesta mudança,
   com os pisos e limites descritos no design. Demais famílias são residuais
   explícitos, não upgrades implícitos ou riscos automaticamente aceitos.
2. Permitir Pillow 13 condicionado a regressão de mídia/PDF. Manter Python 3.12,
   Debian 13, Django 5.2, API e contratos clínicos existentes.
3. Tornar o contexto de build seguro antes de qualquer rebuild e impedir
   persistência do cache de instalação Python no runtime.
4. Reconstruir ambientes a partir de lock atualizado, sem instalar pacotes
   ad hoc no container em execução ou mutar dados para fazer gates passarem.
5. Aceitar evidência por artefato exato, versões instaladas e scan comparável
   com base válida; não usar `latest`, redução numérica ou CI verde como aceite.
6. Separar correção local, revisão de segurança, publicação e implantação.
   Nenhuma dessas etapas autoriza a seguinte automaticamente.

## Alternativas consideradas

### Migrar o digest atual e aceitar todos os avisos implicitamente

Menor mudança técnica imediata, mas transfere riscos prioritários sem decisão
rastreável. Rejeitada como padrão; qualquer exceção precisa ser específica,
temporária e explicitamente aceita pelo operador.

### Atualizar todas as dependências e a distribuição

Pode reduzir mais avisos, porém mistura compatibilidade de várias famílias,
muda o blast radius e dificulta diagnóstico/rollback. Rejeitada neste change.

### Corrigir somente pisos declarados ou remover caches

Diff pequeno e contagem possivelmente menor, mas o runtime pode continuar
vulnerável ou testes executar com versões antigas. Rejeitada: exigir paridade
exata, comportamento e scan do artefato final.

### Corrigir os cinco componentes em slices revisáveis

Selecionada como proposta: cobre os riscos priorizados sem aprovar upgrade de
banco, infraestrutura compartilhada ou mudança funcional. Custa builds e
regressão completos, mas mantém diagnóstico e retorno à baseline delimitados.

## Consequências

### Positivas

- Correção reproduzível de dependências Python e composição nativa auditável.
- Proteção contra envio de secrets/evidências pelo contexto local.
- Aceite de segurança não depende de contagem zero irrealista.
- Migração e publicação continuam decisões operacionais separadas.

### Negativas e trade-offs

- Pillow major exige ensaio, e Django/DRF podem revelar drift de terceiros.
- Dependências vulneráveis fora do alvo continuam exigindo análise futura.
- APT online não garante build bit-a-bit reproduzível somente pelo digest base.
- O ambiente dev precisa de rebuild autorizado, não patch por package manager.

### Riscos e mitigações

- Mudança transitiva ampla: diff do lock por pacote e stop rule de escopo.
- Migration inesperada: checks não mutantes e bloqueio antes de aplicar.
- Queda de alertas enganosa: conferir instalação real e base de scan equivalente.
- Residual esquecido: relatório e aceite com owner, controles e prazo.
- Imagem errada promovida: registrar config/image ID e manifest digest com
  semântica correta; operador seleciona a baseline explicitamente.

## Rollback

Retornar o slice como unidade coerente de declarações, lock, build e testes;
rebuild/recriação apenas com aprovação. Não executar reset, limpeza genérica
ou reversão de dados. A imagem anterior permanece referência de rollback,
sem alegar que suas vulnerabilidades foram resolvidas. Qualquer mudança que
exija schema ou regra nova interrompe este plano e exige nova decisão.

## Referências

- `docs/adr/ADR-0001-deterministic-development-quality-gates.md`.
- `openspec/specs/development-quality-gates/spec.md`.
- `openspec/changes/harden-production-image-security/design.md`.
- `openspec/changes/harden-production-image-security/evidence/baseline.json`.
- Triagem local complementar: `temp/relatorio-triagem-imagem-produtiva.md`.
