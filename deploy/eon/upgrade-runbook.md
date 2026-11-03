# Runbook — Upgrade/atualização da produção no eon

Público e sem segredos: caminhos vêm de `EQMD_APP_DIR`; a versão real
instalada vive no servidor (ver registro privado de implantação).

## Quando usar

Publicar uma nova versão da imagem (novo digest do GHCR gerado pelo CI
após merge em `main`). Nunca build local; nunca tag mutável.

## Pré-requisitos

1. Novo digest confirmado no GHCR (workflow verde; scan `infra-guard` ok).
2. Janela combinada (crons usam `flock -n`: toleram a recriação de
   segundos sem execução dupla; jobs que caírem na janela simplesmente
   rodam na próxima passagem).
3. Acesso ao servidor de implantação com Docker.

## Execução

O script versionado é **`deploy/eon/upgrade.sh`**. Instale-o no diretório
de implantação (o runbook assume `$EQMD_APP_DIR/upgrade.sh`):

```bash
install -m 700 deploy/eon/upgrade.sh "${EQMD_APP_DIR:?}/upgrade.sh"
```

> **Atenção:** o `upgrade.sh` na raiz do repositório é o legado da
> implantação antiga (rootless, com fallback de build local e migrate
> automático). **Não o use no eon.**

```bash
export EQMD_APP_DIR=<diretorio-de-implantacao>
"$EQMD_APP_DIR/upgrade.sh" v0.4.1            # tag (recomendado no dia a dia)
"$EQMD_APP_DIR/upgrade.sh" sha256:<digest>   # digest absoluto
# ou: ... --yes                              # sem confirmações (evite)
```

Tags são **resolvidas para digest** antes de qualquer mudança (a
resolução aparece no gate e fica registrada em `tag-resolved.txt`);
o compose sempre recebe o **digest imutável**, nunca a tag mutável.

O script executa, em ordem: lock exclusivo por implantação → checagem
de coerência dos digests (todos os serviços iguais) → preflight
(estado+disco+compose anterior salvo) → **backup fresco obrigatório**
(db `-Fc` + mídia, com sha256 e teste de não-vazio; aborta se falhar) →
troca do digest no compose (gate + verificação de cobertura total) →
`pull` → `up -d` → `collectstatic` (profile ops) → **migrate gated**
(mostra `--plan`; só aplica com confirmação; no-op é o esperado em
releases de rotina) → health gate **estrito** (`docker inspect`
`Health.Status == healthy` + `/health/` = OK, com aborto ao esgotar
tentativas). Em qualquer falha, o script imprime o caminho de rollback
(com restore de estáticos) e o backup fica em `staging/upgrades/<ts>/`.

Evidências por execução em `<EQMD_APP_DIR>/staging/upgrades/<ts>/`
(ps antes/depois, backup+hashes, compose novo, logs, plano de migrate).

## Pós-upgrade (checklist rápido)

- Login manual na conta do operador;
- dashboard e mapa populando (crons `*/5` seguem normais);
- `journalctl -u cron` sem erros novos em jobs eqmd;
- vizinhas inalteradas (nada do upgrade as toca).

## Rollback

1. Reverter o digest no compose (comando impresso ao final do upgrade
   — e em toda falha, via trap) e `up -d` (recria com a imagem anterior).
2. **Recompor estáticos da versão anterior**: `--profile ops run --rm
init` (o `collectstatic --clear` do upgrade deixou assets novos no
   volume; sem este passo o app antigo serviria com estáticos novos).
3. Validar login e `/health/`.
4. Schema é **forward-only**: rollback curto de app com schema novo é
   tolerado; restaurar backup do banco é procedimento dedicado
   (ver `cutover/rollback.md`), jamais automático.

## Política

- Uma mudança por upgrade (imagem OU compose OR infra), nunca misturar.
- Upgrade não altera env, redes, Caddy ou cron — mudanças nesses pontos
  têm runbooks próprios.
