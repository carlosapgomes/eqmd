# Slice s6 — Runbook de cutover 8h com gates, aborto e rollback

Task refs: `tasks.md` 6.1–6.3 · Change: `migrate-production-to-eon`.

## Objetivo

Consolidar em artefatos operacionais aprováveis a execução da janela
de 8h (fase E), os procedimentos de rollback pré/pós-escrita e os
checklists de aceite/observação (fase F) — **sem executar nada**: todo
comando é template com marcador de GATE para aprovação exata no dia.

## Fontes (somente leitura)

- Plano `temp/relatorio-migracao-eqmd-eon.md` §6 (DNS/redirect), §8
  (fases D/E/F), §9 (gates), §10 (janela/aborto/rollback).
- Artefatos aceitos s2–s5: `docker-compose.eon.yml`,
  `deploy/eon/init/`, `deploy/eon/restore/verify-restore.sql`,
  `deploy/eon/caddy/apply-and-reverse.md`,
  `deploy/eon/cron/install-and-reverse.md`.
- Anexo IPAM (`annexes/ipam-reservation.md`) e decisões do operador
  (`temp/migracao-eon/decisoes-operador-2026-10-30.md`).

## Entregáveis (apenas estes; cada um lint ≤ 80 col, ≤ 450 linhas)

1. `deploy/eon/cutover/runbook.md` (tarefa 6.1) — a janela:
   - Precondições (slices aceitos; s7 medido; data/contatos do
     operador; DNS/Cloudflare preparados; backups do dia feitos).
   - Tabela de TEMPO: início, gates E1–E9 com horários-alvo,
     horário-limite de ABORTO = hora 6, reserva de rollback ≥ 2h.
   - Passos numerados da fase E (avisar usuários → congelar origem
     [manutenção + crontab comentado + esperar ops em voo + PROVAR
     congelamento] → dump final + exportação final de mídia →
     manifesto com hashes nas duas pontas → transferência → restore
     → `verify-restore.sql` + gates → migrations previstas (esperado
     no-op) → ajustes de domínio (`configure_django_site`,
     ALLOWED_HOSTS/CSRF) → subir app/frontend com cron SUSPENSO →
     validação restrita (conta do operador) → decisão go/no-go →
     abrir domínio novo → redirecionamento antigo (302 temporário) →
     E14: reativar cron SOMENTE no destino → origem preservada
     congelada).
   - Cada passo executável: comando template + `GATE:` explícito
     (aprovação exata por comando; nada roda sem isso).
   - Critérios de parada (lista do plano §10.1) e quem decide
     (operador; go/no-go com horário).
   - Referências cruzadas: runbooks gated do Caddy (s4) e cron (s5);
     placeholders `<TEMPO_s7>` para os tempos medidos no s7.
2. `deploy/eon/cutover/rollback.md` (tarefa 6.2):
   - **Pré-escrita**: desabilitar redirect → reativar escritor único
     na origem (INCLUIR preflight obrigatório: inspecionar entrypoint
     do container app da origem — se executa migrate no startup, usar
     caminho seguro SEM `docker start` automático; lição S1b) →
     domínio novo em manutenção → retornar usuários ao endereço
     antigo → comunicar.
   - **Pós-escrita**: congelar AMBOS → backup consistente do destino
     (dump+mídia) → restore reverso PG15→origem (ensaiado no s7) →
     conferir → liberar exatamente um escritor → se não couber na
     janela: manutenção estendida × correção no destino (decisão do
     operador; JAMAIS descartar gravações).
   - Checklist de comunicação (antes/durante/depois; novo login
     esperado — sessões não cruzam domínios).
3. `deploy/eon/cutover/checklist.md` (tarefa 6.3):
   - Aceite funcional binário (§9 do plano): TLS novo domínio, login
     da conta do operador, CSRF, upload/vídeo/PDF, mídia protegida,
     email autorizado, frontend/PWA (sw/manifest), redirecionamento
     sem loop com deep links, vizinhas CHD/HMD/Prisma OK, jobs com
     origem única (primeiras execuções), backup+restore demonstrado.
   - Observação fase F: primeiras 24h, rotina manual do operador
     (banco+mídia+config; registrar destino/retenção), origem
     preservada 14 dias, HTTPS antigo mantido enquanto redireciona.
4. `scripts/tests/test_cutover_docs.mjs` — gate estático (RED
   primeiro): os 3 docs existem; "E1"…"E9" presentes; "hora 6"/aborto
   explícito; reserva ≥ 2h; todo bloco de comando com `GATE:`;
   seções pré-escrita E pós-escrita; referências aos runbooks s4/s5;
   placeholders `<TEMPO_s7`; "14 dias"; `verify-restore.sql`;
   preflight do entrypoint da origem; ausência de "docker start"
   incondicional na reativação da origem.
5. Evidências em `temp/migracao-eon/s6/`.

## Verificação (comandos exatos)

```bash
node --test scripts/tests/test_cutover_docs.mjs
markdownlint-cli2 deploy/eon/cutover/*.md
```

## Restrições

- Nenhum acesso a eon/origem; nada é executado além dos gates de
  lint/teste estático; nenhum `.env`; sem dados reais.
- Tocar SOMENTE os entregáveis; NÃO editar `tasks.md`/`design.md`.
- Comandos são TEMPLATES com variáveis `<...>` — nunca segredo real.

## Definição de pronto

- Gate estático verde; 3 docs lintados (≤80/≤450); mapa E1–E9 binário;
  aborto/reserva explícitos; rollback nos dois regimes com preflight
  S1b; `worker_done` com caminhos, contagem de GATEs e pass counts.
