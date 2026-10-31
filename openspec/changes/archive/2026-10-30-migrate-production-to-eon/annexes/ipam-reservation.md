# Anexo — Reserva IPAM das redes EQMD no eon

Change: `migrate-production-to-eon` · Slice s1 (tarefas 1.1–1.3) ·
Data: 2026-10-30 · Escopo: proposta somente-leitura, sem mutação no eon.

## 1. Objetivo e fontes

Este anexo fecha a análise de conflitos de endereçamento entre as redes
reais do eon, a LAN/VPN do host e as intenções do inventário local
(`infra-single-db`), e registra a reserva proposta das quatro redes
`hospital_*_eqmd`.

Fontes (somente leitura):

- `temp/migracao-eon/eon-reread-2026-10-30.md` — 12 redes Docker
  tabeladas (incluindo `bridge`), LAN `<LAN_CIDR>` e overlay
  Tailscale `100.64.0.0/10`.
- `/projects/dev/infra-single-db/inventory/networks.yaml` — 14
  entradas em `reserved_cidrs` e 10 entradas em `networks`.
- `openspec/changes/migrate-production-to-eon/design.md` (D3).

Ressalva de evidência: o cabeçalho da releitura cita 14 redes, mas a
tabela registra 12 linhas. O verificador usa as 12 linhas tabeladas
(incluindo `bridge`) + LAN + overlay = 14 faixas `occupied`. Redes
efêmeras fora do snapshot permanecem risco residual; qualquer criação
real é gate humano da fase D.

## 2. Faixas ocupadas (`occupied`)

| Rede                     | CIDR               | Observação         |
| ------------------------ | ------------------ | ------------------ |
| `bridge`                 | <CIDR_INTERNO>     | bridge padrão      |
| `<REDE_EDGE>`            | <CIDR_INTERNO>     | caddy/cloudflared  |
| `<REDE_VIZINHA>`         | <CIDR_INTERNO>     | Prisma             |
| `hospital_egress`        | <CIDR_INTERNO>     | worker CHD         |
| `<REDE_BACKUP>`          | <CIDR_INTERNO>     | PG18/backup        |
| `<REDE_BACKUP>`          | <CIDR_INTERNO>     | backup Prisma      |
| `hospital_egress_backup` | <CIDR_INTERNO>     | backup egress      |
| `<REDE_DB_VIZ>`          | <CIDR_INTERNO>     | PG central (CHD)   |
| `<REDE_DB_VIZ>`          | <CIDR_INTERNO>     | PG central (HMD)   |
| `<REDE_TUNEL_VIZ>`       | <CIDR_TUNEL_VIZ>   | cloudflared/caddy  |
| `<REDE_INGRESS_VIZ>`     | <CIDR_INGRESS_VIZ> | web/caddy HMD      |
| `<REDE_EGRESS_VIZ>`      | <CIDR_INTERNO>     | workers HMD        |
| host `enp6s0`            | <LAN_CIDR>         | LAN <LAN_HOSPITAL> |
| host `tailscale0`        | 100.64.0.0/10      | overlay VPN        |

Sem marcação de host = rede Docker do eon (releitura 30/10).

O host é `<LAN_HOSPITAL>`, logo pertence a `<LAN_CIDR>`; a
faixa inteira foi modelada como ocupada para evitar colisão com
endereços vizinhos da LAN.

## 3. Intenções locais (`localIntents`)

O inventário traz duas listas. Ambas entram no verificador porque
`reserved_cidrs` também reserva espaço que o EQMD não pode ocupar sem
uma change própria no repo de infra.

| Lista do inventário | Faixas            | Papel                           |
| ------------------- | ----------------- | ------------------------------- |
| `reserved_cidrs`    | <CIDR_INTERNO>    | espelha o bridge do eon         |
| `reserved_cidrs`    | <CIDR_INTERNO>    | egress CHD retido               |
| `reserved_cidrs`    | <CIDR_VIZ_RESERVA>.0/24 | database futuro (índices 13–16) |
| `reserved_cidrs`    | 172.29.13-16.0/24 | ingress futuro (índices 13–16)  |
| `reserved_cidrs`    | 172.28.13-16.0/24 | egress futuro (índices 13–16)   |
| `networks`          | <CIDR_INTERNO>    | edge compartilhado              |
| `networks`          | <CIDR_INTERNO>    | runtime legado Prisma           |
| `networks`          | <CIDR_INTERNO>    | egress CHD                      |
| `networks`          | <CIDR_INTERNO>    | egress do backup                |
| `networks`          | <CIDR_INTERNO>    | backup do PG central            |
| `networks`          | <CIDR_INTERNO>    | egress Prisma                   |
| `networks`          | <CIDR_INTERNO>    | ingress CHD                     |
| `networks`          | <CIDR_INTERNO>    | ingress Prisma                  |
| `networks`          | <CIDR_INTERNO>    | database CHD                    |
| `networks`          | <CIDR_INTERNO>    | database Prisma                 |

O arquivo JSON canônico usado pelo verificador é
`temp/migracao-eon/ipam-networks.json` (24 intenções, cada uma com
`cidr` e `origin` rastreável ao `id` do inventário).

## 4. Conflitos identificados

### 4.1 Reserva preliminar versus intenções locais

A proposta preliminar (`15.0/29`, `16.0/24`, `17.0/24`, `18.0/24`)
colide com dois slots já reservados no inventário:

| #   | Faixa proposta        | Faixa local                          | Relação |
| --- | --------------------- | ------------------------------------ | ------- |
| C1  | <CIDR_RESERVA_FUTURA> | slot futuro 15 <CIDR_RESERVA_FUTURA> | contida |
| C2  | <CIDR_RESERVA_FUTURA> | slot futuro 16 <CIDR_RESERVA_FUTURA> | igual   |

O verificador acusa exatamente esses dois conflitos (exit 1) quando a
reserva preliminar é testada. A reserva final foi deslocada para
`<CIDR_RESERVA_EQMD>`, os próximos blocos livres.

### 4.2 Faixas do eon versus intenções locais

Há divergência entre a foto do eon e o inventário local:

| #   | Eon (ocupado)      | Inventário (intent) | Relação |
| --- | ------------------ | ------------------- | ------- |
| C3  | <CIDR_TUNEL_VIZ>   | <CIDR_INTERNO>      | contido |
| C4  | <CIDR_INGRESS_VIZ> | <CIDR_INTERNO>      | contido |
| C5  | <CIDR_INTERNO>     | <CIDR_INTERNO>      | igual   |
| C6  | <CIDR_INTERNO>     | <CIDR_INTERNO>      | contém  |
| C7  | <CIDR_INTERNO>     | <CIDR_INTERNO>      | contém  |

Nomes: C3/C4 = `<REDE_TUNEL_VIZ>`/`<REDE_INGRESS_VIZ>` contra
`future_database_index_13`; C5 = `<REDE_EGRESS_VIZ>` contra
`future_database_index_14`; C6 = `<REDE_BACKUP>` contra
`hospital_egress_backup`; C7 = `<REDE_BACKUP>` contra
`<REDE_BACKUP>`.

Interpretação: C3–C5 mostram que os índices 13 e 14 do inventário já
foram consumidos pelas redes HMD no eon; C6–C7 mostram que as redes de
backup planejadas no inventário (`/24`) caem dentro dos `/16` já
existentes no eon. São deriva do inventário, não conflito do EQMD — a
reserva final evita toda a faixa <CIDR_VIZ_RESERVA>. A correção do inventário
pertence a uma change no repo `infra-single-db` e não é decidida aqui.

Sobreposições benignas (mesma rede nos dois inventários, sem ação):
`<CIDR_INTERNO>` (bridge), `<CIDR_INTERNO>` (edge),
`<CIDR_INTERNO>` (Prisma), `<CIDR_INTERNO>` (egress),
`<CIDR_INTERNO>` e `<CIDR_INTERNO>` (databases). O eon também tem
`hospital_egress_backup` `<CIDR_INTERNO>`, ausente do inventário; isso
não afeta a reserva.

### 4.3 LAN e overlay

Nenhuma faixa proposta toca `<LAN_CIDR>` ou `100.64.0.0/10`. Não
há conflito.

## 5. Reserva escolhida

| Rede             | CIDR           | Sizing e uso                    |
| ---------------- | -------------- | ------------------------------- |
| `<REDE_INGRESS>` | <CIDR_INGRESS> | Caddy + frontend; 6 hosts úteis |
| `<REDE_APP>`     | <CIDR_APP>     | app, web e workers; 254 hosts   |
| `<REDE_DB>`      | <CIDR_DB>      | PostgreSQL 15 + backup local    |
| `<REDE_EGRESS>`  | <CIDR_EGRESS>  | saída S3/Telegram; 254 hosts    |

Justificativa:

- Segue a convenção moderna do eon, `172.30.<N>.0/24` por zona, já
  usada por `<REDE_DB_VIZ>` (11), `<REDE_DB_VIZ>` (12) e
  `<REDE_EGRESS_VIZ>` (14).
- Começa em `<CIDR_INGRESS_BASE>`, imediatamente após as faixas ocupadas
  (11–14) e os slots reservados do inventário (15–16), mantendo o
  bloco contíguo.
- `/29` no ingress porque só Caddy e frontend se conectam; `/24` em
  app/db/egress acompanha o dimensionamento das redes vizinhas e
  absorve workers e jobs.
- Nenhuma porta de banco ou gunicorn é publicada (D3); somente o
  ingress recebe Caddy e o cloudflared não acessa containers.

## 6. Alternativas consideradas

1. Reserva preliminar `<CIDR_VIZ_RESERVA>` — rejeitada por C1/C2.
2. Próximo quarteto livre `<CIDR_FALLBACK_EQMD>` (`21.0/29`, `22/24`, `23/24`,
   `24/24`) — fallback se `17–20` for reivindicado antes da fase D.
3. Convenção por plano do inventário no índice 17: database
   `<CIDR_INGRESS_BASE>/24`, ingress `<CIDR_INTERNO>`, egress
   `<CIDR_INTERNO>` — válida, porém diverge da convenção do eon e da
   proposta-base; não escolhida.
4. Liberar os índices 15–16 no inventário — exigiria change no repo
   `infra-single-db`; fora do escopo deste slice.

## 7. Verificação e reprodução

Comando (Node puro, sem dependências, executado no host):

```bash
node scripts/tests/check_ipam_disjoint.mjs \
  temp/migracao-eon/ipam-networks.json
```

Saída capturada (exit code 0):

```text
IPAM disjointness check
input: temp/migracao-eon/ipam-networks.json
sets: occupied=14 localIntents=24 reserved=4

| # | reserved CIDR  | integer range             | conflicts |
| - | -------------- | ------------------------- | --------- |
| 1 | <CIDR_INGRESS> | <CIDR_INGRESS_BASE>-<IP_INTERNO>   | 0         |
| 2 | <CIDR_APP> | <CIDR_APP_BASE>-<CIDR_APP_BROADCAST> | 0         |
| 3 | <CIDR_DB> | <CIDR_DB_BASE>-<CIDR_DB_BROADCAST> | 0         |
| 4 | <CIDR_EGRESS> | <CIDR_EGRESS_BASE>-<CIDR_EGRESS_BROADCAST> | 0         |

result: PASS - 4 reserved blocks disjoint from 14 occupied, 24 local intents
and each other (exit 0)
```

O verificador converte cada CIDR em intervalo inteiro e testa
interseção por containment, não por igualdade de string; qualquer
sobreposição imprime os pares ofensores e retorna exit 1.

## 8. Limites e próximos passos

- Esta reserva é uma **proposta documental**. A criação real das redes
  (`docker network create ...`) é gate humano da fase D, com comando
  exato aprovado.
- A atualização do inventário de redes ocorre em change própria no repo
  `infra-single-db`; este anexo não edita aquele repositório.
- Antes da fase D, repetir o verificador após qualquer mudança de
  inventário ou nova rede no eon; se `17–20` tiver sido ocupado, usar a
  alternativa 2 (`21–24`).
