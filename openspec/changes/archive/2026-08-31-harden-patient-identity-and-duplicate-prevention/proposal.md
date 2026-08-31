# Harden Patient Identity and Duplicate Prevention

## Why

O sistema não possui uma política autoritativa de identidade do paciente nem
proteção global para números de prontuário. Uma auditoria agregada da cópia de
produção encontrou 37 prontuários associados a pacientes distintos, 33 deles
ainda atuais, além de 228 grupos por nome normalizado e nascimento.

A ausência de busca preventiva e de uma garantia concorrente permite novas
colisões em dados clínicos. A correção precisa alertar sobre candidatos sem
bloquear homônimos e reservar prontuários sem consolidar pacientes
automaticamente.

## What Changes

- Introduzir busca de candidatos por nome normalizado, similaridade
  PostgreSQL `pg_trgm` e mesma data de nascimento.
- Exigir revisão explícita antes de criar um paciente quando houver apenas
  correspondência por nome e nascimento; homônimos continuam permitidos.
- Tratar CPF e CNS válidos e coincidentes como evidência forte que impede a
  criação ou atualização conflitante.
- Corrigir a terminologia da interface para CNS, sem referência a carteira de
  plano de saúde.
- Reservar cada número de prontuário globalmente durante todo o histórico,
  inclusive para pacientes excluídos logicamente.
- Tornar atribuições de prontuário imutáveis e não removíveis pelos fluxos
  ordinários; mudanças criam uma nova atribuição histórica.
- Adicionar revalidação transacional e constraint PostgreSQL para fechar a
  janela de concorrência.
- **BREAKING**: a migration da constraint global falhará de forma segura se
  ainda existirem colisões históricas; a consolidação será tratada em outro
  change e deverá preceder o rollout final.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `patients`: passa a definir revisão de identidade na criação/atualização e
  reserva global vitalícia de prontuários.

## Impact

- App principal: `apps/patients`.
- Banco: PostgreSQL, usando extensões existentes `pg_trgm` e `unaccent`, além
  de nova constraint funcional para prontuários.
- Fluxos afetados: criação de paciente, edição de identificadores, criação e
  troca de prontuário, admin e gravações ORM protegidas pela constraint.
- Não há novo pacote externo nem nova API pública obrigatória.
- A consolidação dos dados existentes, qualquer merge clínico e correção em
  massa de CNS permanecem fora deste change.

## Delivery Preconditions

- Risco: **CRÍTICO**, por envolver identidade clínica, migration e
  concorrência.
- A suíte completa precisa voltar a baseline verde antes de qualquer slice ser
  implementado. No ambiente auditado havia 113 falhas e 415 erros.
- O toolchain obrigatório precisa estar disponível no container; `ruff` não
  estava instalado durante o planejamento.
- A constraint final não pode ser aplicada à cópia de produção enquanto a
  auditoria de prontuários não retornar zero colisões canônicas.
