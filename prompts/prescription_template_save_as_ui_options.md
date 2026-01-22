# UI/UX Options for "Save Prescription as Template" Feature

## Overview

**Use Case:** A user creates an outpatient prescription with several drugs commonly prescribed together, then wants to save it as a reusable template (public or private) for future prescriptions.

**Current State:**

- ✅ Prescription templates exist with full CRUD
- ✅ Templates can be public or private
- ✅ Templates can be used when creating prescriptions
- ❌ No way to save an existing prescription as a template

---

## Option 1: Direct Button in Detail Page (Your Idea)

### Placement

In the prescription detail page toolbar, alongside Print, PDF, Edit, Delete buttons:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Voltar] [Timeline]   [Imprimir] [PDF] [Editar] [Salvar como Modelo] [Excluir]  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```html
<button
  type="button"
  class="btn btn-outline-success"
  data-bs-toggle="modal"
  data-bs-target="#saveAsTemplateModal"
>
  <i class="bi bi-file-earmark-plus me-1"></i>
  Salvar como Modelo
</button>
```

### Modal Form

```html
<div class="modal fade" id="saveAsTemplateModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">
          <i class="bi bi-file-earmark-plus me-2"></i>
          Salvar Receita como Modelo
        </h5>
        <button
          type="button"
          class="btn-close"
          data-bs-dismiss="modal"
        ></button>
      </div>
      <div class="modal-body">
        <form id="saveAsTemplateForm">
          <div class="mb-3">
            <label class="form-label">Nome do Modelo *</label>
            <input
              type="text"
              class="form-control"
              name="template_name"
              required
              placeholder="Ex: Hipertensão - Esquema Básico"
            />
          </div>
          <div class="mb-3">
            <label class="form-label">Visibilidade</label>
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                name="is_public"
                value="false"
                id="privateRadio"
                checked
              />
              <label class="form-check-label" for="privateRadio">
                <i class="bi bi-lock me-1"></i> Privado
              </label>
              <div class="form-text">
                Apenas você poderá ver e usar este modelo
              </div>
            </div>
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                name="is_public"
                value="true"
                id="publicRadio"
              />
              <label class="form-check-label" for="publicRadio">
                <i class="bi bi-globe me-1"></i> Público
              </label>
              <div class="form-text">
                Todos os usuários poderão ver e usar este modelo
              </div>
            </div>
          </div>
          <div class="alert alert-info">
            <i class="bi bi-info-circle me-1"></i>
            <strong>{{ prescription_items.count }} medicamentos</strong> serão
            incluídos no modelo.
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
          Cancelar
        </button>
        <button type="button" class="btn btn-success" id="saveTemplateBtn">
          <i class="bi bi-check-circle me-1"></i> Salvar Modelo
        </button>
      </div>
    </div>
  </div>
</div>
```

### Pros

- ✅ Clear and discoverable
- ✅ Follows existing pattern (Edit/Delete buttons in same location)
- ✅ Works well for a feature used occasionally
- ✅ Modal keeps context (user can still see the prescription)

### Cons

- ⚠️ Adds another button to already crowded toolbar
- ⚠️ No visual feedback that this is possible until clicking

---

## Option 2: Dropdown "More Actions" Button

### Placement

Replace Edit/Delete buttons with a dropdown menu:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Voltar] [Timeline]   [Imprimir] [PDF] [Ações ▼]               │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```html
<div class="btn-group" role="group">
  <a href="{{ prescription.get_edit_url }}" class="btn btn-outline-primary">
    <i class="bi bi-pencil me-1"></i>
    Editar
  </a>
  <div class="btn-group">
    <button
      type="button"
      class="btn btn-outline-primary dropdown-toggle"
      data-bs-toggle="dropdown"
      aria-expanded="false"
    >
      Mais Ações
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
      <li>
        <button
          type="button"
          class="dropdown-item"
          data-bs-toggle="modal"
          data-bs-target="#saveAsTemplateModal"
        >
          <i class="bi bi-file-earmark-plus text-success me-2"></i>
          Salvar como Modelo
        </button>
      </li>
      {% if can_delete and perms.events.delete_event %}
      <li><hr class="dropdown-divider" /></li>
      <li>
        <button
          type="button"
          class="dropdown-item text-danger"
          data-bs-toggle="modal"
          data-bs-target="#deleteModal"
        >
          <i class="bi bi-trash me-2"></i>
          Excluir
        </button>
      </li>
      {% endif %}
    </ul>
  </div>
</div>
```

### Pros

- ✅ Reduces toolbar clutter
- ✅ Keeps "Edit" as primary action (most common)
- ✅ "Save as Template" and "Delete" are grouped as less frequent actions
- ✅ Scales well if more actions are added later
- ✅ Similar to existing dropdown patterns in the app (timeline)

### Cons

- ⚠️ Adds one click to reach "Save as Template"
- ⚠️ Less discoverable (hidden behind dropdown)

---

## Option 3: Action Card in Sidebar

### Placement

Add a new card in the sidebar (below Audit Information and Patient Information):

```
┌─────────────────────────────────────────────┐
│  Audit Information                          │
├─────────────────────────────────────────────┤
│  Patient Information                        │
├─────────────────────────────────────────────┤
│  [+] Adicionar como Modelo de Prescrição   │
│                                             │
│  Salve esta receita como um modelo reutilizável│
│  para prescrições futuras.                  │
└─────────────────────────────────────────────┘
```

### Implementation

```html
<div class="card shadow-sm mb-4">
  <div class="card-body">
    <h6 class="card-title mb-3">
      <i class="bi bi-file-earmark-plus text-success me-2"></i>
      Salvar como Modelo
    </h6>
    <p class="small text-muted mb-3">
      Converta esta receita em um modelo reutilizável para prescrições futuras.
    </p>
    <button
      type="button"
      class="btn btn-outline-success w-100"
      data-bs-toggle="modal"
      data-bs-target="#saveAsTemplateModal"
    >
      <i class="bi bi-plus-circle me-1"></i>
      Adicionar como Modelo
    </button>
  </div>
</div>
```

### Pros

- ✅ Doesn't clutter the main toolbar
- ✅ Clearly separated from primary actions
- ✅ Space for explanation text
- ✅ More prominent than a small button
- ✅ Can show additional info (item count, etc.)

### Cons

- ⚠️ Moves action away from other actions (less consistency)
- ⚠️ Might be missed if user doesn't scroll to sidebar
- ⚠️ Takes up sidebar space

---

## Option 4: Inline Action in Prescription Items Card

### Placement

Add an action button above the medication list:

```
┌─────────────────────────────────────────────────────────────────┐
│  Medicamentos Prescritos         [3 medicamentos]               │
│                                                                 │
│  [Adicionar como Modelo]    [Imprimir Lista]                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Medicamento A ...                                            │
│  2. Medicamento B ...                                            │
│  3. Medicamento C ...                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```html
<div
  class="card-header bg-medical-light d-flex justify-content-between align-items-center"
>
  <h5 class="card-title mb-0">
    <i class="bi bi-capsule me-2"></i>
    Medicamentos Prescritos
  </h5>
  <span class="badge bg-medical-primary">
    {{ prescription_items.count }} medicamento{{
    prescription_items.count|pluralize }}
  </span>
</div>
<div class="card-body p-3 bg-light">
  <div class="d-flex gap-2">
    <button
      type="button"
      class="btn btn-outline-success btn-sm"
      data-bs-toggle="modal"
      data-bs-target="#saveAsTemplateModal"
    >
      <i class="bi bi-file-earmark-plus me-1"></i>
      Salvar como Modelo
    </button>
    <button
      type="button"
      class="btn btn-outline-secondary btn-sm"
      onclick="window.print()"
    >
      <i class="bi bi-printer me-1"></i>
      Imprimir Lista
    </button>
  </div>
</div>
```

### Pros

- ✅ Contextually relevant (next to the actual medications)
- ✅ Doesn't clutter main toolbar
- ✅ Clear connection to the items being saved

### Cons

- ⚠️ Inside a card (less standard pattern)
- ⚠️ Could be confused with item-level actions
- ⚠️ Might be missed if user doesn't scroll to that section

---

## Option 5: Floating Action Button (FAB)

### Placement

A floating button that appears in the bottom-right corner:

```
                                            ┌──────┐
                                            │  +   │
                                            └──────┘
```

### Implementation

```html
<div class="position-fixed bottom-0 end-0 p-3" style="z-index: 100;">
  <button
    type="button"
    class="btn btn-success btn-lg rounded-circle shadow"
    data-bs-toggle="modal"
    data-bs-target="#saveAsTemplateModal"
    title="Salvar como Modelo"
  >
    <i class="bi bi-file-earmark-plus"></i>
  </button>
</div>
```

With tooltip showing:

- On hover: "Salvar receita como modelo"
- After save: Success checkmark

### Pros

- ✅ Always visible (no scrolling needed)
- ✅ Modern pattern used in many apps
- ✅ Doesn't affect existing layout

### Cons

- ⚠️ Covers content on small screens
- ⚠️ Less discoverable for users unfamiliar with pattern
- ⚠️ Might be confused with "Add" button (common use for FAB)
- ⚠️ Overkill for an occasional action

---

## Option 6: Quick Action in Items List

### Placement

Add a "Save all as template" option in each item row, with visual connection:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Medicamento A                                              │
│     [Editar] [Excluir] [Salvar todos como Modelo →]            │
├─────────────────────────────────────────────────────────────────┤
│  2. Medicamento B                                              │
│     [Editar] [Excluir] [Salvar todos como Modelo →]            │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```html
<div class="d-flex justify-content-between align-items-center mt-2">
  <small class="text-muted">
    <i class="bi bi-info-circle me-1"></i>
    Salvar todos os itens como modelo
  </small>
  <button
    type="button"
    class="btn btn-sm btn-outline-success"
    data-bs-toggle="modal"
    data-bs-target="#saveAsTemplateModal"
  >
    <i class="bi bi-file-earmark-plus me-1"></i>
    Salvar Modelo
  </button>
</div>
```

### Pros

- ✅ Contextually clear (saves the items you're looking at)
- ✅ Repetitive (visible for each item)

### Cons

- ⚠️ Confusing (which item's button do I click?)
- ⚠️ Repetitive visual clutter
- ⚠️ Non-standard pattern

---

## Option 7: Progressive Disclosure (Smart Button)

### Placement

Button appears conditionally based on usage patterns:

**First time**: Show tooltip/hint: "Dica: Você pode salvar esta receita como um modelo!"

**Frequent user**: Always show "Salvar como Modelo" button in toolbar

**Infrequent user**: Hide button, show in dropdown menu

### Implementation

```html
{% if show_save_as_template_hint %}
<div class="alert alert-success alert-dismissible fade show mb-3" role="alert">
  <i class="bi bi-lightbulb me-2"></i>
  <strong>Dica:</strong> Gostou desta receita? Salve-a como um modelo para usar
  novamente!
  <button
    type="button"
    class="btn-close"
    data-bs-dismiss="alert"
    aria-label="Close"
  ></button>
  <div class="mt-2">
    <button
      type="button"
      class="btn btn-success btn-sm"
      data-bs-toggle="modal"
      data-bs-target="#saveAsTemplateModal"
    >
      <i class="bi bi-file-earmark-plus me-1"></i>
      Salvar como Modelo
    </button>
  </div>
</div>
{% else %}
<!-- Regular button or dropdown -->
{% endif %}
```

### Pros

- ✅ Educates users about the feature
- ✅ Adapts to user behavior
- ✅ Reduces clutter for power users

### Cons

- ⚠️ Complex to implement (needs tracking)
- ⚠️ Inconsistent UI across users

---

## Comparison Table

| Option                        | Toolbar Clutter | Discoverability  | Context | Implementation |
| ----------------------------- | --------------- | ---------------- | ------- | -------------- |
| **1. Direct Button**          | High            | Very High        | Low     | Simple         |
| **2. Dropdown**               | Low             | Medium           | Low     | Simple         |
| **3. Sidebar Card**           | None            | Medium           | Medium  | Simple         |
| **4. Inline in Card**         | None            | High             | High    | Simple         |
| **5. FAB**                    | None            | Low (unfamiliar) | Low     | Simple         |
| **6. Quick Action in Items**  | Low             | High             | High    | Complex        |
| **7. Progressive Disclosure** | Varies          | High             | Low     | Complex        |

---

## Recommendations

### Primary Recommendation: Option 2 (Dropdown "More Actions")

**Rationale:**

1. ✅ Best balance of clutter reduction vs. discoverability
2. ✅ Follows existing patterns in your app (timeline dropdowns)
3. ✅ Scales well if more actions are added later
4. ✅ Keeps "Edit" as primary action (most common use case)
5. ✅ Groups less frequent actions logically

**Implementation:**

```
Toolbar: [Voltar] [Timeline] [Imprimir] [PDF] [Editar] [Mais Ações ▼]
                                                └─ Salvar como Modelo
                                                └─ Excluir
```

---

### Secondary Recommendation: Option 1 (Direct Button) + Progressive Disclosure

**Rationale:**

1. ✅ Maximum discoverability for new feature
2. ✅ Follows dailynotes pattern (Direct "Duplicar" button)
3. ✅ Combine with hint/tooltip to educate users
4. ✅ Can move to dropdown later if toolbar gets too crowded

**Implementation:**

```
Toolbar: [Voltar] [Timeline] [Imprimir] [PDF] [Editar] [Salvar como Modelo] [Excluir]

+ Optional: Show hint alert above prescription items on first visit
```

---

### Alternative for Power Users: Option 4 (Inline in Prescription Items Card)

**Rationale:**

1. ✅ Most contextually relevant placement
2. ✅ Clear what's being saved (the medications)
3. ✅ Doesn't add to toolbar
4. ✅ Could be used IN ADDITION to dropdown option

**Implementation:**

```
Medications Card Header: [X medicamentos] [Salvar como Modelo] [Imprimir Lista]
```

---

## Hybrid Approach (Best of Both Worlds)

Combine multiple options for different user segments:

### Implementation

```html
<!-- Main action in dropdown -->
<div class="btn-group">
  <a href="{{ prescription.get_edit_url }}" class="btn btn-outline-primary">
    <i class="bi bi-pencil me-1"></i> Editar
  </a>
  <button
    class="btn btn-outline-primary dropdown-toggle"
    data-bs-toggle="dropdown"
  >
    Mais
  </button>
  <ul class="dropdown-menu">
    <li>
      <button
        class="dropdown-item"
        data-bs-toggle="modal"
        data-bs-target="#saveAsTemplateModal"
      >
        <i class="bi bi-file-earmark-plus text-success me-2"></i>
        Salvar como Modelo
      </button>
    </li>
    <!-- other actions -->
  </ul>
</div>

<!-- ALSO: Contextual button in medications card for discoverability -->
<div
  class="card-header bg-medical-light d-flex justify-content-between align-items-center"
>
  <h5 class="card-title mb-0">Medicamentos Prescritos</h5>
  <button
    type="button"
    class="btn btn-sm btn-outline-success"
    data-bs-toggle="modal"
    data-bs-target="#saveAsTemplateModal"
    title="Salvar receita como modelo"
  >
    <i class="bi bi-file-earmark-plus me-1"></i> Salvar como Modelo
  </button>
</div>

<!-- AND: One-time hint for new users -->
{% if should_show_template_hint %}
<div class="alert alert-info alert-dismissible fade show mt-3">
  <i class="bi bi-lightbulb me-2"></i>
  <strong>Sabia?</strong> Você pode salvar esta receita como um modelo para usar
  novamente!
  <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
{% endif %}
```

### Benefits

- ✅ Multiple entry points = high discoverability
- ✅ Dropdown for organized action management
- ✅ Inline button for contextual access
- ✅ One-time hint to educate users
- ✅ Can hint can be dismissed, reducing long-term clutter

---

## Additional UX Considerations

### Success Feedback

After saving as template, show:

1. Success toast notification
2. Button to "Ver Modelo" (link to template detail)
3. Option to "Criar nova receita com este modelo"

### Validation

- Require at least 1 medication to save
- Require template name
- Warn if template with same name exists (for this user)

### Permissions

- Only doctors and residents can create templates (same as existing)
- Show template creator in template list
- Respects existing `is_public` field

### Analytics

Consider tracking:

- How often users save prescriptions as templates
- Public vs. private ratio
- Most common medication combinations saved
