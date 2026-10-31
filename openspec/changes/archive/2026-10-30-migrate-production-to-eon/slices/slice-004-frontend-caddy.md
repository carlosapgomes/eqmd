# Slice s4 — Frontend/estáticos, snippet Caddy reversível e PWA

Task refs: `tasks.md` 4.1–4.3 · Change: `migrate-production-to-eon`.

## Objetivo

Definir e validar o serviço `frontend` (estáticos imutáveis +
reverse proxy com o comportamento da origem), decidir e pinar a
imagem dele por digest, reproduzir o tratamento PWA
(`sw.js`/`manifest.json`) e o limite de upload, e produzir o snippet
Caddy da rota EQMD com procedimento exato de aplicação/reversão e
checklist de smoke das vizinhas — **sem tocar no eon**.

## Entregáveis (apenas estes)

1. `deploy/eon/frontend/nginx.conf` — comportamento espelhando a
   origem: `client_max_body_size 60m`; `/static/` servido do volume
   (ro) com headers corretos; **`/static/sw.js` e `/manifest.json`
   com `Cache-Control: no-cache`** (comportamento especial da
   origem); `/media/` **sempre proxado ao Django** (mídia protegida
   por autorização — nunca servida direta do disco do frontend);
   demais caminhos proxados a `eqmd:8000`; headers de proxy reais
   (`X-Forwarded-For/Proto/Host`); gzip off para sw.js? (manter
   simples e fiel à origem; comentar divergências).
2. Imagem do frontend DECIDIDA: `nginx` estável (paridade com a
   origem), pinada por digest no `docker-compose.eon.yml` (igual aos
   outros serviços; obter digest via `docker manifest inspect` —
   consulta read-only ao registry, sem usar tag mutável em artefato).
   Ajustar: remover `EQMD_FRONTEND_IMAGE` do env (compose passa a
   pinar), extender init para `collectstatic` no volume
   `eqmd_static`, montar ro no frontend; manter 12+ invariantes
   verdes (atualizar as que citavam a var).
3. `deploy/eon/caddy/equipemed.caddyfile` — snippet da rota
   `equipemed.projetoshgrs.com` para o `frontend` pela rede
   `<REDE_INGRESS>` (sem TLS local — termina no edge/CF;
   seguir o padrão das rotas existentes do HMD já vistas no plano).
4. `deploy/eon/caddy/apply-and-reverse.md` — procedimento GATED
   (fase D): baseline do Caddyfile atual, backup, comando exato de
   aplicação (com `admin off` documentado: `caddy reload` NÃO é
   garantido → método de recriação do container com janela curta),
   smoke pós-aplicação das vizinhas (**CHD/ats, HMD e
   Prisma/<APP_VIZINHA>**), e **reversão exata** (restaurar backup +
   recriar + re-smoke). Nada executa aqui; é runbook aprovável.
5. `scripts/tests/test_frontend_static.mjs` — invariáveis do
   `nginx.conf` (RED primeiro): 60m, no-cache em sw.js/manifest,
   `/media/` proxado (não servido), proxy para eqmd:8000, ausência
   de root em /media, headers forwarded.
6. `scripts/tests/test_frontend_e2e.mjs` — ensaio docker descartável
   (`eqmd_s4_*`, cleanup garantido): frontend (nginx digest pinado)
   - stub backend (container python http.server como "app") + volume
     estático sintético (com `sw.js` e `manifest.json` sintéticos);
     asserts via curl: static 200 + content-type; **sw.js e manifest
     com `Cache-Control: no-cache`**; proxy 200 (stub recebe path);
     POST 61 MB → **413** e POST pequeno → 2xx (limite 60m provado);
     `/media/x` chega ao STUB (prova que não é servido direto);
     cleanup zero-resíduo comprovado.
7. Evidências em `temp/migracao-eon/s4/`.

## Verificação (comandos exatos)

```bash
node --test scripts/tests/test_frontend_static.mjs
node scripts/tests/test_frontend_e2e.mjs
node --test scripts/tests/test_compose_eon.mjs
```

## Restrições

- Nenhum acesso ao eon/origem; consulta de digest via
  `docker manifest inspect` é permitida (read-only); PULL local da
  imagem nginx pinada permitido SOMENTE para o ensaio descartável.
- Descartáveis `eqmd_s4_*`; nunca tocar containers/redes/volumes
  existentes; sem `.env`; sem dados reais.
- Tocar SOMENTE os entregáveis (+ `docker-compose.eon.yml`/
  `env.eon.example` conforme item 2); NÃO editar `tasks.md`/
  `design.md`; Markdown lintado ≤ 80 colunas (item 4).
- DNS/Cloudflare/hostname continuam responsabilidade do operador
  (registrar no apply-and-reverse.md como pré-requisito).

## Definição de pronto

- Gates verdes (static + e2e + compose 12+/12); digest nginx pinado
  documentado; snippet + reversão aprováveis; evidências salvas.
- `worker_done` com: caminhos, pass counts, digest escolhido,
  resultados do 413/no-cache/proxy e cleanup.
