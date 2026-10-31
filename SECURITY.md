# Security Policy

## Reporting a Vulnerability

Use o contato privado do mantenedor (Security Advisories do repositório).
Relatos são respondidos em até 7 dias.

## O que este repositório NÃO contém (por design)

Este é um projeto livre e público de software clínico. Detalhes de
**implantação de produção** são deliberadamente mantidos FORA da árvore
rastreada:

- endereços IP internos, CIDRs e topologia de rede do ambiente
  hospitalar;
- nomes internos de servidores, redes, aliases e aplicações vizinhas;
- credenciais e valores reais de ambiente (arquivos `env*` reais são
  ignorados pelo Git).

Arquivos implantáveis usam **placeholders** (`<EQMD_APP_DIR>`,
`<REDE_INGRESS>`, `<CIDR_APP>` etc.) ou variáveis resolvidas pelo env
(`EQMD_NET_*`). Os valores reais vivem apenas no ambiente de
implantação e no repositório privado de infraestrutura.

## Guardiões automatizados

- `.githooks/pre-commit`: bloqueia endereços RFC1918/CGNAT em arquivos
  rastreados (padrão estrutural; allowlist em `.githooks/infra-allow`).
- `.github/workflows/infra-guard.yml`: mesmo scan no CI, em pushes,
  PRs e uma varredura semanal completa.

## Histórico

Detalhes internos que chegaram ao histórico em 2026-10 foram
removidos via reescrita (`git filter-repo`) — ver ADR-0005 e o
registro privado de implantação.
