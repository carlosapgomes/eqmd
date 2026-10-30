# Production image security dossier

Escopo: artefato exato da mudança `harden-production-image-security`
(slice `eqmd-sec-003b`). Data de referência: 2026-10-30.
Run de evidência: `run_9de7b1f04726`.

Este dossiê é **técnico**. Ele não aceita risco residual, não publica
imagem e não autoriza implantação; essas decisões permanecem humanas
(ver §9). O candidato não é a baseline produtiva.

## 1. Identidades do artefato

Tag não é prova de identidade. Os valores abaixo vêm do daemon e do
arquivo OCI exportado (`docker save`), não do nome `eqmd:s3a-candidate`.

Candidato qualificado (build local, não publicado):

- tag local: `eqmd:s3a-candidate` (apenas referência de trabalho);
- daemon `.Id` / OCI index digest:
  `sha256:615585d9edbe9e2b9498d1db6dadae170145085e8b5728d33c1feb1cdf92a808`;
- manifest amd64:
  `sha256:bd00fb7fd75071474219a92e91c6d91fa55e21aaf282bc50dd6246b83820c397`;
- config digest:
  `sha256:25b991b7c9ed1568f3c5b80502aedd40100fcea9d74aed474dcf29ecf0efd72a`;
- tar `docker save`:
  `c9d91ce74a58b9a04b564362c0f5a1b265b1ddca641e1bb2a6a61b78233ce6ba`;
- criado em `2026-10-30T16:32:13-03:00`, 2.277.730.959 bytes,
  `linux/amd64`, 14 layers, Python 3.12.16, Debian 13.

Baseline produtiva (referência, não alterada):

- `ghcr.io/carlosapgomes/eqmd@sha256:7087e3e0621d69b1b2be7e8029d712187f9ae3b8875f81f5e8fd90fd35637b8f`;
- config `sha256:d876c9cb4e6a221b06788a37ff769eea6a18a46e42aa2bf02473064914021cba`;
- revisão `6e2928c8d205ccb698bdbbd1bb48c281723cfa28`, 13 layers,
  Python 3.12.15.

O scan usa `docker-archive`; o `manifestDigest` que o Grype reporta
(`sha256:1d783e12…` no candidato, `sha256:4cc3a448…` na baseline) é um
manifesto re-serializado pelo Syft a partir do arquivo, **não** o digest
OCI nem o digest de registry. Não usar esse valor como identidade do
artefato.

## 2. Proveniência

- Base pinada por digest:
  `python:3.12-slim-trixie@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159`.
  As 4 primeiras layers do candidato são exatamente as layers dessa
  base. Build registrado sem cache de `uv`/`pip`.
- Sexteto de fontes conferido por SHA-256: `pyproject.toml`,
  `uv.lock`, `Dockerfile`, `scripts/tests/test_security_image_build.mjs`,
  `apps/core/tests/test_security_runtime.py`,
  `apps/mediafiles/tests/test_image_security_compatibility.py`.
- Paridade instalado × `uv.lock`: 87 de 88 `dist-info` Python casam
  exatamente (0 divergências de versão); o restante é `pip`. Os 17
  pacotes do lock ausentes são o grupo `dev` (runtime sem
  `INSTALL_DEV`). `libbrotli1` é pacote Debian, verificado por `dpkg`.
- Gate Node `scripts/tests/test_security_image_build.mjs` executado
  contra o candidato: 6/6 pass, incluindo o novo sentinela `.venv`.

### Histórico do defeito (registro obrigatório)

O primeiro candidato S3a
(`sha256:972f68b1…`, config `sha256:76aebb29…`, tar `3f5ff322…`)
embarcava um `/app/.venv` de 260 MB copiado pelo `COPY . .`, porque o
`.dockerignore` não excluía `.venv`. Esse venv continha Django 5.2.1,
DRF 3.16.0, certifi 2025.6.15 e Pillow 12.0.0, e
`/app/.venv/bin/python` importava essas versões. O scan S3b detectou
100 matches dos alvos dentro do venv; R3/D5 não foram atendidos.

Correção autorizada e aplicada: `.venv/` no `.dockerignore` e
`.venv/pyvenv.cfg` no conjunto de sentinelas do gate de contexto
(arquivo mantido em 450 linhas). Rebuild com
`docker build --target production -t eqmd:s3a-candidate .` (contexto
de 389,34 MB para 375,16 kB). O candidato defeituoso **não** é
utilizável; sua evidência fica preservada em
`temp/security-hardening/s3b/provenance/` e `.../scans/` (tar, JSON e
TSVs). O rebuild removeu a imagem antiga do daemon; o tar é a cópia
remanescente.

## 3. Alvos corrigidos

| Alvo    | Baseline   | Candidato       | Adv. | Matches |
| ------- | ---------- | --------------- | ---- | ------- |
| Brotli  | 1.1.0-2+b7 | 1.1.0-2+deb13u1 | 1    | 0       |
| Django  | 5.2.1      | 5.2.18          | 34   | 0       |
| DRF     | 3.16.0     | 3.18.3          | 5    | 0       |
| certifi | 2025.6.15  | 2026.10.23      | 1    | 0       |
| Pillow  | 12.0.0     | 13.0.0          | 60   | 0       |

Brotli é o pacote `libbrotli1`; DRF é Django REST framework;
Adv. = advisories históricos na baseline.

Total: os 101 advisories históricos da baseline são exatamente os 101
do scan fresco da baseline, e **nenhum** aparece no candidato. Não há
advisory novo nos cinco alvos na base atual.

## 4. Configuração do scan

- Scanner: `anchore/grype`
  `sha256:0dcdcaa6036655f926b847c843f67558e67fedc90a286160156a344cb187331c`,
  Grype 0.110.0 / Syft 1.42.3, containers descartáveis.
- Base: cache congelada `temp/security-hardening/s1b/grype-db`,
  schema `v6.1.10`, built `2026-10-30T06:23:28Z`, `valid` antes e
  depois; hashes dos arquivos idênticos antes/depois.
- `GRYPE_DB_AUTO_UPDATE=false`, `GRYPE_DB_CACHE_DIR=/root/.cache/grype`
  explícito, `validate-age=true`, escopo `squashed`.
- Mesmos flags nos dois artefatos; sem `--only-fixed`, sem
  `--fail-on`, sem config/ignore/VEX; JSON preservado com todos os
  `fix.state`.
- Regra de validade da base: 5 dias. Idade no run: ~13 h. Base
  inválida/vencida exige `grype db update` sob aprovação separada.
- Autorização: plano `temp/security-hardening/s3b/scan-plan-v1.md`
  (sha256 `05f4260e79ed…`) aprovado por humano; rebuild e gate
  adicionais aprovados na mesma release.

## 5. Comparação

| Métrica               | Baseline | Candidato |
| --------------------- | -------- | --------- |
| Matches totais        | 2.168    | 2.042     |
| Critical              | 63       | 48        |
| High                  | 552      | 492       |
| Medium                | 518      | 483       |
| Low                   | 117      | 101       |
| Negligible            | 865      | 865       |
| Unknown               | 53       | 53        |
| Advisory IDs únicos   | 801      | 686       |
| `fix.state=fixed`     | 309      | 183       |
| `fix.state=not-fixed` | 957      | 957       |
| `fix.state=wont-fix`  | 902      | 902       |

A queda de 126 matches decompõe-se em 101 advisories dos alvos
removidos e 25 matches de atualizações nativas da base (curl/libcurl
12, expat 6, django-allauth 3, python 2, setuptools 1, libjxl 1).
Nenhum estado foi filtrado. Contagem menor não é aceite de risco.

## 6. Risco residual (não aceito)

Residual do candidato, por família (matches de instância, não CVEs
únicas):

| Família                    | Versão           | Matches | Critical | High |
| -------------------------- | ---------------- | ------- | -------- | ---- |
| binutils (8 binários)      | 2.44-3           | 552     | 0        | 0    |
| pypdf                      | 5.8.0            | 60      | 0        | 13   |
| curl/libcurl (3 pacotes)   | 8.14.1-2+deb13u7 | 117     | 18       | 39   |
| ffmpeg/libav\* (6 pacotes) | 7.1.5-0+deb13u1  | 234     | 6        | 138  |
| python (stdlib)            | 3.12.16          | 7       | 0        | 0    |
| libexpat1                  | 2.9.0-1~deb13u1  | 5       | 0        | 0    |
| django-allauth             | 65.8.1           | 3       | 0        | 0    |

Distribuição por tipo: 1.858 `deb`, 173 `python`, 7 `binary`,
4 `rust-crate`. As famílias fora dos cinco alvos (pypdf, PyJWT,
AnyIO, FFmpeg/Poppler, curl, binutils) seguem sem correção neste
change e precisam de decisão explícita do operador. O Grype também
aplica suas supressões padrão de `kernel-headers` de forma idêntica
nos dois scans, preservadas separadamente.

## 7. Limitações

- Snapshot de advisories; não demonstra explorabilidade nem substitui
  análise de risco. Nenhum PoC foi executado.
- Contagem por instância de pacote infla famílias com vários binários
  (binutils, curl, ffmpeg); a comparação válida é por advisory e
  versão, não pelo total.
- APT online não é bit-a-bit reproduzível: a composição nativa é
  auditada por manifesto/scan, não por promessa de snapshot.
- O candidato não tem label `org.opencontainers.image.revision`; a
  rastreabilidade vem dos hashes de fonte, do log de build e da
  cadeia de evidências.
- O candidato é local e não publicado: não existe RepoDigest GHCR
  para ele; não inventar um.
- S3b não reexecutou a suíte completa: ela é herdada do S3a (mesmo
  lock e mesmo código de aplicação); apenas contexto de build e gate
  Node mudaram. Qualquer novo rebuild exige renovar os gates de
  runtime.
- `eqmd_dev` e containers preservados não foram tocados.

## 8. Retorno e retomada da baseline

Não há deploy a reverter e nenhuma migration foi executada. Para
voltar à baseline:

1. continuar usando a imagem por digest
   `ghcr.io/carlosapgomes/eqmd@sha256:7087e3e0…` (presente no host);
2. não reutilizar o candidato defeituoso `sha256:972f68b1…`;
3. se autorizado, remover apenas a tag local do candidato
   (`docker image rm eqmd:s3a-candidate`), sem remover a baseline;
4. reexecutar o par de scans com o mesmo plano e a mesma base, ou
   atualizar a base sob aprovação separada.

## 9. Fronteira humana

Aceitação de qualquer residual, publicação no GHCR, escolha de versão
de release, promoção do candidato e implantação são decisões
**humanas** e permanecem pendentes. Este dossiê não concede exceção,
não substitui a baseline e não autoriza migração.

## 10. Evidência

- `temp/security-hardening/s3b/provenance/` — identidades, hashes,
  inventário do candidato e do defeito.
- `temp/security-hardening/s3b/scans/` — primeiro par de scans e o
  achado `.venv`.
- `temp/security-hardening/s3b/requal/` — build, gate, tar, scans e
  comparação do candidato requalificado.
- `/tmp/<APP_VIZINHA>-slice-eqmd-sec-003b-report.md` — relatório do slice.
