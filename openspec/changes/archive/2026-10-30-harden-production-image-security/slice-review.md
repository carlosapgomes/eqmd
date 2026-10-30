# Revisão de dimensionamento dos slices

## Parecer

Revisão de 29/10/2026 usando `openspec-vertical-change-writer`.
**Decompor S1 e S3; manter S2.** Resultado: três famílias e cinco unidades
executáveis, sem implementar nenhum deles nesta revisão.

Não mudaram os cinco componentes, pisos, API, estratégia de runtime, gates de
segurança, autorizações ou fronteiras de produção. A atualização do design é
somente de sequência e responsabilidade de verificação. Não foi necessário
reabrir a ADR/spec; eles não dependiam de uma quantidade específica de slices.

## Diagnóstico e menor divisão correta

| Família | Problema anterior                       | Resultado da divisão |
| ------- | --------------------------------------- | -------------------- |
| S1      | Contexto + build nativo + cache/scan    | S1a e S1b            |
| S2      | Resolver e contrato HTTP/OIDC           | Manter inteiro       |
| S3      | Pillow major + regressão + qualificação | S3a e S3b            |

### S1a: fronteira de contexto

Tem falha determinística própria: sentinela privada atravessa o builder.
O resultado observável é um artefato de fixture com dados privados excluídos e
recursos-controle preservados. Não precisa resolver APT, atualizar base ou
recriar o dev. Isso elimina um pré-requisito de segurança do rebuild seguinte.
Não é um slice só de teste: entrega a exclusão real e sua prova de ponta a ponta.

### S1b: runtime nativo

Com o contexto já aceito, pode focar base/Brotli/cache e integração nativa.
O resultado é imagem construída/inspecionada com versão corrigida e recursos
preservados. Separar cache em outra unidade não trouxe benefício suficiente:
base, instalação e conteúdo final são verificados no mesmo artefato.

### S2: manter framework e TLS juntos

Django e DRF compartilham resolução, autenticação, CSRF, HTTP e OIDC. Dividi-los
produziria rebuilds e combinações intermediárias pouco úteis antes da mesma
regressão. certifi é uma alteração pequena de piso/lock no envelope já definido;
não justifica outra unidade só pelo número de pacotes.

### S3a: comportamento de mídia

Pillow major exige diagnóstico funcional próprio. A unidade termina com todos
os seus testes e candidato identificado. Nenhum teste devido à atualização é
adiado para a unidade seguinte; não precisa simultaneamente classificar todo
risco residual do sistema para concluir a regressão de mídia.

### S3b: qualificação end-to-end

Entrega evidência operacional baseline/candidato, identidade, alvos corrigidos
e residual do mesmo artefato. É capacidade de verificação de segurança, não
slice horizontal de documentação. Não pode editar implementação ao descobrir
falha: devolve evidência e bloqueio, separando correção de aceitação.

## Rastreabilidade do contrato anterior

| Requisito original                  | Contrato ativo responsável        |
| ----------------------------------- | --------------------------------- |
| S1 R1 — contexto seguro             | S1a R1–R3                         |
| S1 R2 — Brotli/cache                | S1b R1–R2                         |
| S1 R3 — lock/recursos preservados   | S1a R4 e S1b R2–R3                |
| S1 R4 — candidato intermediário     | S1b R4                            |
| S2 R1–R4                            | S2 R1–R4, sem alteração de escopo |
| S3 R1 — Pillow                      | S3a R1                            |
| S3 R2 — imagem/PDF/vídeo/permissões | S3a R2                            |
| S3 R3 — candidato e cinco alvos     | S3a R3 e S3b R1–R3                |
| S3 R4 — residual/gate humano        | S3a R4 e S3b R4                   |

## Coerência para worker fresh

- `tasks.md` referencia as cinco unidades e seus critérios de verificação.
- Os dois arquivos únicos anteriores foram renomeados para índices `group-*`,
  sem manter um contrato executável antigo que concorra com os novos.
- Cada `slice-*.md` tem R1..Rn, failing-before, gates, aceite, escalada, relatório
  e stop rule; nenhum depende da conversa anterior.
- Relatórios são individuais; evidência de uma unidade aceita é entrada da
  próxima, não autorização para executá-la.
- Fonte de contexto/targets, baseline portátil, ADR/spec/design e testes
  relevantes têm referências explícitas.
- Build/recriação e proteção contra startup `migrate` continuam precondições
  operacionais de D4, não permissões novas ou decisões escondidas na divisão.
- Não há commit, publish, deploy, atualização de tasks pelo worker ou aceitação
  automática de riscos residuais.

## Alteração externa observada no workspace

No início da revisão, `git status --short` não mostrava
`scripts/tests/test_security_image_build.mjs`. Na conferência final, esse teste
apareceu como não rastreado. Não foi criado, alterado ou executado por esta
revisão, e sua autoria/conclusão não foi presumida.

O operador confirmou que outro LLM havia iniciado S1, interrompeu esse agente
e autorizou remover os arquivos criados. Foi removido somente o teste externo
identificado, além dos diretórios vazios `temp/security-hardening/s1a/` e seu
pai. Não havia alteração em Dockerfile, contexto ou dependências a reverter.
ADR/índice e artefatos deste planejamento foram preservados. Nenhuma task foi
marcada concluída nem o trabalho abortado foi aceito por coincidência de path.
Os índices substituídos não autorizam continuar o contrato antigo.

## Próximo passo

Com a reconciliação concluída, revisar e autorizar somente
`slices/slice-001a-safe-build-context.md`. As cinco unidades permanecem
pendentes de autorização e aceite; 4/4 artefatos OpenSpec completos significa
planejamento completo, não correção implementada. Esta revisão não construiu
imagem nem alterou dependências.
