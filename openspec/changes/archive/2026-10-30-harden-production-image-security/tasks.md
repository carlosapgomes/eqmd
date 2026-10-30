# Tasks

Status: change tecnicamente completa — S1a, S1b, S2, S3a e S3b
aceitos após revisão independente. Aceite S3b: ACCEPT P0/P1/P2=0
(reviewer Pi codex/gpt-6-luna, decisão de lane do operador para
preservar cota Muse; OpenCode2 é implementador). Candidato final:
eqmd:s3a-candidate sha256:615585d9..., cinco alvos zerados, 2042
matches residuais (48C/492H) documentados no dossiê. Aceite de risco
residual, publicação, promoção e implantação permanecem decisões
humanas do operador. Reviewer/coordenador atualiza este arquivo, não o
implementador.

## 1. Família S1 — Build seguro e Brotli corrigido

### S1a — Contexto de build

Contrato: `slices/slice-001a-safe-build-context.md`.

- [x] 1.1 S1a: demonstrar inclusão indevida com sentinelas sintéticas no builder
      isolado; verificar RED por conteúdo indevido, não por erro de infraestrutura.
- [x] 1.2 S1a: corrigir exclusões e provar controles permitidos/proibidos;
      verificar teste Docker real, gates do projeto e relatório S1a independente.

### S1b — Runtime nativo

Pré-condição: S1a revisado e aceito.
Contrato: `slices/slice-001b-native-runtime-and-brotli.md`.

- [x] 1.3 S1b: demonstrar Brotli anterior/cache persistente e adicionar os
      controles de imagem; verificar failing-before reproduzível no relatório.
- [x] 1.4 S1b: corrigir base/Brotli/cache sem mudar lock Python; verificar
      comparação dpkg, manifesto nativo, instalação real e cache ausente.
- [x] 1.5 S1b: provar recursos nativos, contexto preservado e gates em runtime
      novo; entregar scan do alvo Brotli e relatório intermediário sem deploy.

## 2. S2 — Framework HTTP e confiança TLS

Pré-condição: S1b revisado e aceito.
Contrato: `slices/slice-002-http-and-tls-dependencies.md`.

- [x] 2.1 S2: registrar RED dos pisos Django/DRF/certifi e regressões
      HTTP/CSRF/OIDC; verificar falha das versões anteriores, sem
      confundir import quebrado com RED.
- [x] 2.2 S2: atualizar só alvos/transientes necessários e reconstruir ambiente
      autorizado; verificar paridade exata de declaração, lock e instalação.
- [x] 2.3 S2: executar regressão focada, suíte, check e drift não mutante;
      entregar relatório com diff seletivo e zero schema novo.

## 3. Família S3 — Mídia e qualificação de segurança

### S3a — Pillow e compatibilidade

Pré-condição: S2 revisado e aceito.
Contrato: `slices/slice-003a-pillow-compatibility.md`.

- [x] 3.1 S3a: demonstrar Pillow anterior e cobrir JPEG/PNG/WebP/thumbnail/PDF
      com fixtures sintéticas; verificar RED e contratos negativos/permissões.
- [x] 3.2 S3a: atualizar Pillow/lock e reconstruir runtime aprovado; verificar
      paridade dos pisos e regressão completa, sem upgrade oculto de pypdf.
- [x] 3.3 S3a: entregar candidato com fonte/identidade/manifestos e relatório de
      compatibilidade; verificar que testes devidos à atualização terminaram aqui.

### S3b — Qualificação do artefato

Pré-condição: S3a revisado e aceito.
Contrato: `slices/slice-003b-artifact-qualification.md`.

- [x] 3.4 S3b: conferir candidato exato, fonte, versões e gates de S3a;
      verificar proveniência sem editar dependências/código ou confiar só em tag.
- [x] 3.5 S3b: analisar baseline/candidato com base/política válidas equivalentes;
      verificar alvos históricos/atuais, supressões e composição residual.
- [x] 3.6 S3b: entregar dossiê e relatório com riscos e procedimento de retorno;
      verificar que aceite residual, publicação e implantação continuam humanos.
