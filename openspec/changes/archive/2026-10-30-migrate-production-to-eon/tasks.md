# Tasks: Migração da produção EQMD para o eon (etapa 1)

## 1. IPAM e reserva de redes

- [x] 1.1 Compilar faixas reais do eon (tabela de drift do plano +
      inventário `infra-single-db`) e detectar conflitos com as
      reservas locais
- [x] 1.2 Propor CIDRs para as quatro redes `*_eqmd` sem colisão,
      com justificativa e alternativas
- [x] 1.3 Registrar a proposta como anexo do design (evidência em
      `temp/migracao-eon/`); atualização do inventário da infra fica
      em change própria naquele repo

## 2. Compose eon e configuração

- [x] 2.1 Escrever `docker-compose.eon.yml` autossuficiente (eqmd,
      postgres, frontend, init, migrate) com imagem por digest,
      redes `external: true`, sem portas de DB/app publicadas
- [x] 2.2 Criar `env.eon.example` sintético e validar
      `docker compose config` apenas com sintéticos (RED: nenhuma
      validação existente; GREEN: config renderiza sem secrets)
- [x] 2.3 Definir UID/GID não privilegiado e política de permissões
      de mídia/logs/tmp; hardening incremental (read_only, tmpfs,
      cap_drop, no-new-privileges) com o que for comprovado
      funcional no ensaio

## 3. PostgreSQL 15 dedicado

- [x] 3.1 SQL de init: template UTF8/C, database, extensões
      (`unaccent`, `pg_trgm`), role runtime não superusuária e
      identidade migrator com grants/default privileges
- [x] 3.2 Procedimento de dump/restore lógico (`pg_dump -Fc` →
      `pg_restore` com `--exit-on-error`), conferência de objetos,
      sequences, constraints e ownership
- [x] 3.3 Ensaio local descartável do restore com dados sintéticos
      e evidências (logs, contagens agregadas, sem dados clínicos)

## 4. Frontend, estáticos e Caddy

- [x] 4.1 Especificar e validar serviço de estáticos + proxy
      (imagem/digest, coleta na operação init, somente leitura)
- [x] 4.2 Reproduzir o tratamento de `sw.js`/`manifest.json` e
      limites de upload; smoke de frontend/PWA no ensaio
- [x] 4.3 Snippet Caddyfile da rota EQMD + procedimento exato de
      aplicação e reversão (admin off); checklist de smoke das
      vizinhas (CHD/HMD/Prisma) para aprovação do operador

## 5. Cronjobs

- [x] 5.1 Definir os 5 jobs no destino (mecanismo, usuário,
      timezone, locks) com suspensão até o aceite e reativação
      pós-cutover; Firebase permanece desativado
- [x] 5.2 Evidenciar execução única (lock) e horário correto com
      timezone validado no ensaio

## 6. Runbook de cutover

- [x] 6.1 Runbook da janela de 8h: passos numerados com comandos
      exatos a aprovar, gates E1–E9, horário-limite de aborto (h6),
      reserva de rollback (≥2h)
- [x] 6.2 Procedimentos de rollback pré-escrita e pós-escrita
      (incluindo restore reverso PG15) e checklist de comunicação
- [x] 6.3 Checklist de aceite funcional (conta do operador) e de
      observação pós-cutover (Fase F)

## 7. Ensaio e2e local

- [x] 7.1 Executar rehearsal completo no Zen com dados sintéticos:
      dump → manifesto com hashes → "transferência" → restore em
      PG15 descartável → init/migrate → boot → gates funcionais
- [x] 7.2 Cronometrar todas as etapas e consolidar os tempos no
      plano de janela (reserva de rollback e aborto)
- [x] 7.3 Registrar limites do ensaio (dados sintéticos, sem rede
      real do eon, sem DNS/Cloudflare) e o que só pode ser validado
      no destino
