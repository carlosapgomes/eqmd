# Slice s1 — Reconciliação IPAM e reserva de redes EQMD

Task refs: `tasks.md` 1.1–1.3 · Change: `migrate-production-to-eon`.

## Objetivo

Fechar a análise de conflitos de endereçamento entre as redes reais do
eon, a LAN/VPN do host e as intenções do inventário local
(`infra-single-db`), e produzir a reserva proposta das quatro redes
`hospital_*_eqmd` com verificação determinística e evidências.

## Entradas (somente leitura)

- `temp/migracao-eon/eon-reread-2026-10-30.md` — redes/CIDRs reais do
  eon (releitura autorizada de 30/10), LAN `<LAN_CIDR>`,
  tailscale `<IP_VPN>/32` (overlay `100.64.0.0/10`).
- `/projects/dev/infra-single-db/inventory/networks.yaml` —
  reservas/intenções arquiteturais LOCAIS (repo externo: NÃO editar).
- `openspec/changes/migrate-production-to-eon/design.md` (D3).

## Entregáveis (apenas estes arquivos)

1. `temp/migracao-eon/ipam-networks.json` — dados de entrada da
   verificação: `occupied` (eon + LAN + overlay), `localIntents`
   (inventory) e `reserved` (proposta), cada CIDR com origem anotada.
2. `scripts/tests/check_ipam_disjoint.mjs` — verificador determinístico
   em Node puro (sem deps), executável no host: valida que `reserved`
   é disjunto de `occupied` E de `localIntents` E entre si (detecta
   sobreposição por containment, não só igualdade); imprime tabela
   resumo; exit 0 somente se tudo disjunto.
3. `openspec/changes/migrate-production-to-eon/annexes/ipam-reservation.md`
   — anexo do design: análise de conflitos (incluindo conflitos entre
   `occupied` do eon e `localIntents` do inventário, se houver),
   reserva escolhida com justificativa (convenção `172.30.N.0/24`,
   sizing: /29 ingress, /24 app/db/egress), alternativas (próximos
   blocos livres) e o comando de verificação para reprodução.
   NÃO contém secrets; CIDRs internos já documentados no plano.

## Passos

1. Extrair `occupied` da evidência de releitura (12 redes + bridge +
   LAN + overlay tailscale).
2. Extrair `localIntents` do `networks.yaml` (rotular cada entrada).
3. Escolher `reserved` a partir de `<CIDR_RESERVA_FUTURA>` (proposta preliminar:
   ingress 15.0/29, app 16.0/24, db 17.0/24, egress 18.0/24),
   ajustando se o verificador acusar conflito com intents locais —
   nesse caso documentar o conflito e a alternativa escolhida.
4. Escrever o verificador; executar
   `node scripts/tests/check_ipam_disjoint.mjs temp/migracao-eon/ipam-networks.json`
   e capturar saída + exit code.
5. Escrever o anexo citando a saída do verificador e a evidência de
   origem; rodar `markdownlint-cli2` no anexo.

## Verificação (comandos exatos)

```bash
node scripts/tests/check_ipam_disjoint.mjs \
  temp/migracao-eon/ipam-networks.json
# esperado: exit 0, tabela com 4 reserved disjuntas

markdownlint-cli2 \
  openspec/changes/migrate-production-to-eon/annexes/ipam-reservation.md
# esperado: 0 erros
```

## Restrições

- Nenhuma operação no eon/origem; nenhum comando Docker; nenhum
  arquivo fora dos três entregáveis; NÃO editar `tasks.md`,
  `design.md` ou o repo `infra-single-db`.
- Node no host apenas (sem python local; regras do AGENTS.md valem
  para qualquer python, que não é necessário aqui).
- Se `networks.yaml` tiver intent conflitante irredutível com a
  convenção do eon, NÃO decidir sozinho: registrar conflito no anexo e
  apontar decisão pendente ao coordenador.

## Definição de pronto

- Verificador exit 0 com a reserva final; saída anexada ao relatório.
- Anexo lint-clean com: conflitos analisados, reserva + alternativas,
  sizing, referência às evidências, nota de que a criação real das
  redes é gate humano da fase D e que a atualização do inventário da
  infra ocorre em change própria naquele repo.
- `worker_done` com: caminhos dos 3 arquivos, exit code do verificador,
  conflitos encontrados (ou "nenhum") e a reserva final em 4 linhas.
