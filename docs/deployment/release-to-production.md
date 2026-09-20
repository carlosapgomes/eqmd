# Release e upgrade de produção

## Objetivo

Este runbook descreve o caminho completo entre a criação de uma release e o
upgrade da instalação rootless de produção.

A produção usa `upgrade-rootless.sh`. O antigo
`upgrade-rootless-transition.sh` não faz mais parte do fluxo operacional.

## Contrato de versionamento

O Git usa tags com prefixo `v`, enquanto as imagens usam a versão sem o
prefixo:

| Artefato              | Exemplo                                  |
| --------------------- | ---------------------------------------- |
| Git tag               | `v1.2.3`                                 |
| Imagem completa       | `ghcr.io/carlosapgomes/eqmd:1.2.3`       |
| Imagem da linha minor | `ghcr.io/carlosapgomes/eqmd:1.2`         |
| Imagem do commit      | `ghcr.io/carlosapgomes/eqmd:sha-abcd123` |

Produção DEVE usar a tag completa, como `1.2.3`. As tags `latest` e `1.2` são
mutáveis e não identificam de forma permanente um único artefato.

## Comportamento do workflow

O workflow `.github/workflows/build-and-push.yml` publica imagens em dois
casos:

- push para `main`;
- push de uma Git tag que corresponda a `v*`.

Um push para `main` publica `main`, `latest` e `sha-...`. Uma tag `v1.2.3`
publica `1.2.3`, `1.2` e `sha-...`.

O workflow recusa uma release tag cujo commit não pertença ao histórico de
`main`. Pull requests são validados por `.github/workflows/ci-pr.yml` e não
publicam imagens.

## 1. Preparar a release

Execute esta etapa em uma estação de desenvolvimento, não no servidor de
produção.

1. Confirme que todas as alterações da release foram revisadas e integradas em
   `main`.
2. Confirme que os checks obrigatórios de `main` passaram.
3. Escolha a nova versão semântica:
   - `MAJOR` para quebra de compatibilidade;
   - `MINOR` para funcionalidade compatível;
   - `PATCH` para correção compatível.
4. Confirme que a árvore local está limpa.

Exemplo para a versão `0.3.0`:

```bash
git switch main
git pull --ff-only
git status --short
git log -1 --oneline
```

Não continue se houver alterações locais inesperadas.

## 2. Criar e publicar a Git tag

Crie uma tag anotada no commit de `main` que será publicado:

```bash
VERSION=0.3.0
GIT_TAG="v${VERSION}"

git tag -a "$GIT_TAG" -m "Release ${GIT_TAG}"
git push origin "$GIT_TAG"
```

Não mova nem reutilize uma tag já publicada. Se uma release estiver incorreta,
corrija o código e publique uma nova versão.

## 3. Aguardar e verificar a imagem

No GitHub Actions, aguarde o workflow **Build and Push Docker Image** terminar
com sucesso para a tag.

A imagem esperada será:

```bash
VERSION=0.3.0
IMAGE="ghcr.io/carlosapgomes/eqmd:${VERSION}"
```

Verifique se o manifesto existe:

```bash
docker manifest inspect "$IMAGE" >/dev/null
```

Para um pacote privado, autentique antes com uma credencial que possua somente
as permissões necessárias:

```bash
docker login ghcr.io
```

A criação da tag publica imagens, mas não cria automaticamente uma entrada de
GitHub Release. Quando forem necessárias notas formais, crie a GitHub Release
pela interface web ou, opcionalmente, com:

```bash
gh release create "$GIT_TAG" --generate-notes
```

## 4. Preparar o servidor de produção

Acesse o servidor com o usuário rootless responsável pelo deployment. Não use
`root` nem `sudo` para os comandos Docker.

Defina os valores da release:

```bash
VERSION=0.3.0
GIT_TAG="v${VERSION}"
IMAGE="ghcr.io/carlosapgomes/eqmd:${VERSION}"
COMPOSE_FILE=docker-compose.rootless.yml
ENV_FILE=.env.rootless
```

Entre no diretório do projeto e confira a árvore antes de trocar a revisão:

```bash
cd /caminho/para/eqmd
git status --short
```

Pare se houver alterações rastreadas inesperadas. Não use `git reset --hard` ou
`git clean` para tentar corrigi-las.

Busque as tags e use exatamente a revisão da release:

```bash
git fetch origin --tags --prune
git checkout --detach "$GIT_TAG"
```

Confirme o commit:

```bash
RELEASE_COMMIT="$(git rev-list -n 1 "$GIT_TAG")"
test "$(git rev-parse HEAD)" = "$RELEASE_COMMIT"
```

## 5. Fixar a imagem da release

Edite `.env.rootless` e defina a imagem completa:

```bash
EQMD_IMAGE=ghcr.io/carlosapgomes/eqmd:0.3.0
```

Não use `latest` em produção. Confirme o valor efetivo sem imprimir outras
variáveis do arquivo:

```bash
grep '^EQMD_IMAGE=' "$ENV_FILE"

docker compose \
  -f "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  config --images
```

O serviço da aplicação deve apontar para a versão completa escolhida.

## 6. Executar o dry-run

O dry-run não altera containers, imagens ou banco de dados:

```bash
COMPOSE_FILE="$COMPOSE_FILE" \
ENV_FILE="$ENV_FILE" \
./upgrade-rootless.sh --dry-run
```

Revise no plano:

- arquivo Compose e arquivo de ambiente corretos;
- imagem versionada correta;
- backup do banco habilitado;
- URL de health check correta;
- serviço da aplicação e serviço PostgreSQL corretos.

Não use `SKIP_DB_BACKUP=1` em uma atualização normal de produção.

## 7. Executar o upgrade

Execute dentro da janela de manutenção:

```bash
COMPOSE_FILE="$COMPOSE_FILE" \
ENV_FILE="$ENV_FILE" \
./upgrade-rootless.sh
```

O script deverá:

1. salvar uma cópia do arquivo de ambiente;
2. criar uma tag local de rollback para a imagem atual;
3. gerar um dump PostgreSQL;
4. baixar a imagem versionada;
5. recriar o serviço da aplicação;
6. executar migrations Django;
7. configurar o Django Site quando aplicável;
8. executar `collectstatic`;
9. validar o endpoint de saúde.

Acompanhe a saída. Se o pull da imagem versionada falhar e o script anunciar um
build local de fallback, interrompa o procedimento e investigue o registry. Um
build local não é o artefato versionado aprovado para a release.

## 8. Verificar o deployment

Confirme o estado dos serviços:

```bash
docker compose \
  -f "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  ps
```

Confira o endpoint de saúde:

```bash
curl -f "http://localhost:${HOST_PORT:-8778}/health/"
```

Confirme que o container executa a imagem configurada:

```bash
APP_CONTAINER_ID="$(
  docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$ENV_FILE" \
    ps -q eqmd
)"

docker inspect "$APP_CONTAINER_ID" \
  --format 'image={{.Config.Image}} image_id={{.Image}}'
```

Compare a revisão gravada na imagem com o commit da release:

```bash
IMAGE_ID="$(
  docker inspect "$APP_CONTAINER_ID" --format '{{.Image}}'
)"
IMAGE_REVISION="$(
  docker image inspect "$IMAGE_ID" \
    --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}'
)"
RELEASE_COMMIT="$(git rev-list -n 1 "$GIT_TAG")"

echo "release=${RELEASE_COMMIT}"
echo "image=${IMAGE_REVISION}"
test "$IMAGE_REVISION" = "$RELEASE_COMMIT"
```

Por fim, faça um smoke test funcional autenticado das operações clínicas
críticas da release.

## 9. Falhas e rollback

O script cria, antes do upgrade:

- uma tag local da imagem anterior;
- um dump do PostgreSQL;
- uma cópia do arquivo de ambiente.

Os caminhos e comandos de rollback aparecem no resumo do próprio script.
Registre essa saída no ticket ou evidência da release.

Se o health check falhar, o script tenta restaurar automaticamente a imagem
anterior. Essa restauração de imagem não desfaz migrations já aplicadas.

Se uma migration falhar:

1. não execute o upgrade novamente às cegas;
2. preserve logs, dump e diretório de backup;
3. determine quais migrations foram aplicadas;
4. avalie a compatibilidade da imagem anterior com o schema atual;
5. restaure o banco somente com plano aprovado e janela de manutenção.

A restauração de banco é uma operação destrutiva e nunca deve ser executada
apenas porque a aplicação foi revertida.

## 10. Encerrar a release

Registre como evidência:

- Git tag e commit;
- URL do workflow concluído;
- tag e digest da imagem;
- diretório de backup criado pelo upgrade;
- resultado das migrations;
- resultado do health check;
- resultado do smoke test funcional;
- horário de início e término;
- operador responsável.

Depois de validar produção, publique ou complete as notas da GitHub Release.
Mantenha a imagem anterior e o backup pelo período definido na política de
retenção.

## Checklist rápido

- [ ] Alterações integradas em `main`
- [ ] CI de `main` verde
- [ ] Tag anotada `vX.Y.Z` criada a partir de `main`
- [ ] Workflow da tag concluído com sucesso
- [ ] Imagem `X.Y.Z` disponível no registry
- [ ] Servidor na revisão exata `vX.Y.Z`
- [ ] `.env.rootless` usando `X.Y.Z`, não `latest`
- [ ] Dry-run revisado
- [ ] Backup PostgreSQL habilitado
- [ ] Upgrade concluído
- [ ] Health check aprovado
- [ ] Commit da imagem igual ao commit da tag
- [ ] Smoke test funcional aprovado
- [ ] Evidências da release registradas
