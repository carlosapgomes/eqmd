# Convenções de Branch e Commit (eqmd)

## 1) Modelo de branch (solo dev)

- `main`: sempre estável e potencialmente releasável
- branch curta por change:
  - `feat/<change-id>-<slug>`
  - `fix/<change-id>-<slug>`
  - `chore/<slug>`

Exemplos:

- `feat/add-simplenotes-validation-service`
- `fix/patient-transfer-bed-sync`
- `chore/devloop-ci-bootstrap`

## 2) Política de merge

- Merge em `main` apenas por PR
- PR com checks obrigatórios verdes
- PR pequeno (preferência: 1 slice vertical)

## 3) Conventional Commits (obrigatório)

Formato:

```text
type(scope): summary
```

Tipos recomendados:

- `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `build`, `perf`

Exemplos:

- `feat(simplenotes): add note visibility service`
- `fix(patients): prevent invalid transfer status`
- `test(events): add draft expiration scenarios`
- `docs(workflows): add devloop migration guide`

## 4) Regras práticas de commit

- Um commit deve representar uma unidade lógica clara.
- Evitar commit “genérico” (`update`, `ajustes`, etc.).
- Preferir commit rastreável ao change/slice.

## 5) Relação com OpenSpec

Quando houver change OpenSpec:

- referenciar o `change-id` no PR
- manter tasks sincronizadas com os commits
- fechar o ciclo do slice antes de iniciar o próximo
