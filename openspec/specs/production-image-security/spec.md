# production-image-security Specification

## Purpose

Garantir que a imagem entregue para implantação contenha os componentes de
segurança aprovados, preserve os contratos clínicos e HTTP e apresente evidência
auditável de vulnerabilidades e riscos residuais do artefato exato.

## Requirements

### Requirement: Componentes prioritários corrigidos no artefato instalado

A imagem candidata MUST atender aos pisos de segurança aprovados para Django,
DRF, Pillow, certifi e Brotli. A versão realmente instalada MUST ser verificada,
não inferida apenas de declarações, cache, tag ou contagem total de CVEs.

#### Scenario: Os cinco componentes atendem ao contrato

- **WHEN** o candidato final é avaliado
- **THEN** as versões instaladas atendem ao design aprovado e ao lock aplicável
- **AND** o scan válido não encontra versões afetadas dos cinco alvos
- **AND** a identidade do artefato é registrada sem confundir digests distintos

#### Scenario: Apenas um cache vulnerável foi removido

- **WHEN** a contagem cai mas um componente instalado continua afetado
- **THEN** o candidato MUST ser rejeitado como correção incompleta

### Requirement: Dependências resolvidas de forma delimitada

O change MUST manter Python 3.12, Django 5.2 e Debian 13, com lock Python
reproduzível e alterações transitivas justificadas. Upgrade fora da fronteira
aprovada MUST exigir nova decisão antes de implementação adicional.

#### Scenario: Resolver exige atualização de outra família

- **WHEN** um alvo não pode ser corrigido sem mudança material fora do escopo
- **THEN** o worker MUST retornar bloqueio com a evidência do conflito
- **AND** MUST NOT aceitar uma atualização global para obter lock resolvido

#### Scenario: Gate executa em dependências anteriores

- **WHEN** o lock mudou mas o ambiente de teste ainda usa versões antigas
- **THEN** a paridade exata MUST falhar
- **AND** a suite verde anterior MUST NOT ser apresentada como validação nova

### Requirement: Contexto e imagem sem dados privados de operação

A construção MUST excluir secrets, backups, mídia/logs locais e evidências
operacionais, inclusive `temp/`. A imagem final MUST NOT persistir cache de
instalação Python. Provas de exclusão MUST usar fixtures sintéticas, sem enviar
secrets reais ao builder como parte do teste.

#### Scenario: Workspace contém nomes de secrets e cache de scan

- **WHEN** o teste isolado constrói o contexto com sentinelas sintéticas
- **THEN** o artefato MUST excluir os caminhos proibidos
- **AND** MUST preservar código e recursos necessários aos targets existentes

#### Scenario: Pacotes de runtime foram instalados

- **WHEN** a imagem final é inspecionada
- **THEN** os pacotes necessários MUST estar presentes sem o cache de instalação
- **AND** o manifesto nativo e a base usada MUST ser auditáveis

### Requirement: Contratos funcionais e de persistência preservados

A correção MUST preservar login, autorização, CSRF, OIDC, HTTP, imagem, PDF e
vídeo, sem novas migrations ou alteração de schema/dados. Tests MUST usar
fixtures sintéticas e PostgreSQL, com gates existentes mantidos sem waivers.

#### Scenario: Dependências novas passam a regressão

- **WHEN** os gates executam em ambiente reconstruído do lock atualizado
- **THEN** a suíte completa e checks de drift MUST passar
- **AND** imagens válidas JPEG/PNG/WebP e fluxos de PDF/vídeo MUST continuar úteis
- **AND** entradas inválidas e acesso não autorizado MUST continuar negados

#### Scenario: Uma atualização exige mudança de schema ou contrato

- **WHEN** a resolução ou o check revela migration nova ou quebra pública
- **THEN** a execução MUST parar para revisão de escopo
- **AND** MUST NOT gerar migration de fornecedor ou alterar regra clínica

### Requirement: Scan auditável do candidato exato

A avaliação MUST usar scanner e base válidos, identidade exata do artefato e
política comparável entre baseline e candidato. Resultados suprimidos e todos
os estados de correção MUST permanecer distinguíveis. Erro operacional MUST
ser bloqueio, não convertido em aprovação informativa.

#### Scenario: Comparação de dois artefatos usa bases diferentes

- **WHEN** a evidência histórica não permite comparação equivalente
- **THEN** ambos MUST ser reanalisados com a mesma base válida
- **AND** a validação de idade/hash MUST NOT ser desligada

#### Scenario: Candidato possui outros alertas

- **WHEN** os alvos foram corrigidos mas permanecem avisos fora do escopo
- **THEN** o relatório MUST listar os residuais e mudanças materiais
- **AND** MUST NOT declarar segurança apenas por workflow verde ou redução total

### Requirement: Gate humano separado da execução técnica

Worker MUST NOT aceitar risco residual, publicar imagem ou alterar produção
por concluir um slice. A promoção de candidato e qualquer exceção MUST ter
aceite explícito do operador, com justificativa, controles e prazo verificáveis.

#### Scenario: Candidato termina os testes locais

- **WHEN** o implementador produz o relatório de slice
- **THEN** MUST parar para revisão independente
- **AND** MUST NOT começar outro slice, publicar ou iniciar migração

#### Scenario: Uma exceção é proposta

- **WHEN** um aviso residual não tem correção ou depende de condição ausente
- **THEN** a decisão MUST permanecer pendente até o aceite do operador
- **AND** MUST NOT ser inferida de baixa criticidade operacional ou do CI verde
