# Proposal: Correção delimitada de segurança da imagem produtiva

## Why

O scan autorizado de 29/10/2026 confirmou 2.166 matches na imagem produtiva,
com 61 Critical e 540 High, incluindo componentes realmente instalados e
utilizados pelo aplicativo. Precisamos reduzir os riscos prioritários antes
da migração de host, sem transformar esse trabalho em upgrade geral ou deploy.

## What Changes

- Corrigir cinco componentes delimitados: Django na série 5.2, Django REST
  framework, Pillow, certifi e Brotli da imagem Debian 13.
- Usar pisos de segurança verificados e resolução seletiva em `uv.lock`;
  impedir atualização irrestrita de todas as dependências.
- **BREAKING técnico, não funcional:** permitir Pillow 13 em vez de 12,
  condicionado a regressão de uploads, formatos, thumbnails e PDFs.
  Não aprovar mudança de contrato clínico ou de API.
- Impedir inclusão de secrets, evidências `temp/`, backups e caches locais
  no contexto da imagem; impedir cache de instalação persistido no runtime.
- Produzir candidato por digest, verificar versões instaladas, compatibilidade
  e scan com base válida; decidir riscos residuais sem supressão automática.
- Separar construção/aceite de segurança de publicação, implantação e migração.

## Capabilities

### New Capabilities

- `production-image-security`: contrato verificável de componentes corrigidos,
  contexto seguro, compatibilidade e aceite de artefato por digest.

### Modified Capabilities

Nenhuma. A série Django 5.2, lock autoritativo e gates não mutantes continuam
regidos por `development-quality-gates`; o novo piso é uma restrição adicional
compatível, não autorização para Django 6 ou waiver de qualidade.

## Included Scope

| Componente | Piso proposto   | Limite de escopo               |
| ---------- | --------------- | ------------------------------ |
| Django     | 5.2.17          | `<5.3`                         |
| DRF        | 3.18.2          | `<3.19`                        |
| Pillow     | 13.0.0          | `<14`                          |
| certifi    | 2026.10.18      | Versão concreta fixada no lock |
| libbrotli1 | 1.1.0-2+deb13u1 | Debian 13; comparação via dpkg |

Os quatro releases Python existem no PyPI, não estão yanked e seus metadados
aceitam Python 3.12. Isso não substitui resolução, testes ou scan do candidato.
Se pisos deixarem de resolver os avisos atuais, parar para revisão do contrato.

## Excluded Scope

- PostgreSQL 15 para 18, Eon, redes, Caddy, Cloudflare, domínio e Compose.
- Atualização ampla de pypdf, PyJWT, AnyIO, cryptography, urllib3 ou frontend.
- Reativar Firebase, Matrix, Element ou bots; remover bibliotecas por suposição.
- Refatoração de parsers/arquitetura de workers, schema ou fluxos clínicos.
- Deploy, migrations aplicadas, backups reais, commits, push ou publicação.
- Alterar scanner/CI já corrigido, ignorar CVEs para obter um scan verde ou
  prometer zero vulnerabilidades na imagem inteira.

Dependências transitivas só podem mudar quando comprovadamente necessárias aos
cinco alvos, com diff de resolução explicado. Conflito material exige decisão.

## Risk Assessment

**CRÍTICO / HIGH/ARCH**, por análise manual: autenticação/framework, contrato
HTTP, segurança e disponibilidade dos parsers são quatro critérios afetados.
Isso é risco técnico da correção, não mudança da classificação de missão do
sistema de apoio hospitalar. Não há mudança de persistência autorizada.

Requer ADR Proposed, ensaio sintético, TDD/failing-before por slice, suíte
verde, comparação de scan e revisão independente. A ADR proposta é
`docs/adr/ADR-0004-bounded-production-image-security-remediation.md`.

## Impact

Superfícies esperadas: `Dockerfile`, `.dockerignore`, `pyproject.toml`,
`uv.lock`, testes de segurança/compatibilidade e documentação de evidência.
O plano possui três famílias de trabalho e cinco unidades executáveis:
S1a → S1b → S2 → S3a → S3b, com revisão entre elas. A decomposição e o mapa de
requisitos estão em `slice-review.md`. Estes artefatos não autorizam
implementação; o trabalho externo abortado foi reconciliado nessa revisão.

A baseline portátil de advisories está em `evidence/baseline.json`; relatórios
brutos e dados clínicos não devem ser versionados. Os scans não provam alcance
explorável de todos os matches, e os avisos fora do alvo continuam pendentes.

## Success Criteria

1. Candidato mantém Python 3.12/Debian 13, Django 5.2 e PostgreSQL 15.
2. Os cinco pisos são atendidos nas instalações reais do artefato e os
   advisories-alvo não afetam as versões instaladas no scan de aceite.
3. Contexto/artefato não incorporam secrets, backups, evidências ou caches.
4. Login, CSRF, OIDC, HTTP, imagem, PDF e vídeo mantêm contratos existentes;
   `./scripts/test.sh` e checks de migrations passam sem schema novo.
5. Comparação usa digest e base compatíveis; riscos residuais são reportados,
   nunca aceitos automaticamente pelo implementador.
6. Há relatório por slice, procedimento de retorno à baseline e nenhuma
   alteração produtiva implícita. Publicação/implantação exigem novo aceite.
