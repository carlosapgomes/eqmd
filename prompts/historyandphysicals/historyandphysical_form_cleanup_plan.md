# HistoryAndPhysical Form Template Cleanup Plan

## Template: `historyandphysical_form.html`

**Current Purpose**: Used only to edit/update an existing historyandphysical  
**New Name**: Should be renamed to `historyandphysical_update_form.html`

## Current Issues Analysis

After analyzing the template, I identified several areas where code designed for dual-purpose (create/edit) functionality exists but is only used for editing:

### 1. Dual-Purpose Title Logic (Lines 5-11)

```django
{% if form.instance.pk %}
  Editar Anamnese e Exame Físico - {{ form.instance.patient.name }}
{% else %}
  Nova Anamnese e Exame Físico
{% endif %}
```

**Issue**: The `{% else %}` branch is never used since this template is only for editing.

### 2. Dual-Purpose Header Text (Lines 87-94)

```django
{% if form.instance.pk %}
  Editar Anamnese e Exame Físico
{% else %}
  Nova Anamnese e Exame Físico
{% endif %}
```

**Issue**: Same conditional logic with unused `else` branch.

### 3. Dual-Purpose Card Title (Lines 121-125)

```django
{% if form.instance.pk %}
  Editar Informações da Anamnese e Exame Físico
{% else %}
  Informações da Nova Anamnese e Exame Físico
{% endif %}
```

**Issue**: Only the editing branch is used.

### 4. Dual-Purpose Button Text (Lines 217-221)

```django
{% if form.instance.pk %}
  Atualizar Anamnese e Exame Físico
{% else %}
  Salvar Anamnese e Exame Físico
{% endif %}
```

**Issue**: Only the update button is used.

### 5. Complex Breadcrumb Logic (Lines 68-83)

**Issue**: Contains conditional logic for both create and edit scenarios, with unused create branch.

### 6. Complex Navigation Logic (Lines 96-113)

```django
{% if form.instance.pk %}
  <!-- Edit-specific buttons -->
{% else %}
  <!-- Create-specific buttons (unused) -->
{% endif %}
```

**Issue**: Create branch is unused.

## Cleanup Plan

### Step 1: File Renaming

- [ ] Rename `historyandphysical_form.html` to `historyandphysical_update_form.html`
- [ ] Update all references to this template in views, URLs, and other templates

### Step 2: Remove Dual-Purpose Logic

- [ ] **Title Block** (Lines 5-11): Replace with single edit title: `Editar Anamnese e Exame Físico - {{ form.instance.patient.name }}`
- [ ] **Main Header** (Lines 87-94): Replace with: `Editar Anamnese e Exame Físico`
- [ ] **Card Title** (Lines 121-125): Replace with: `Editar Informações da Anamnese e Exame Físico`
- [ ] **Submit Button** (Lines 217-221): Replace with: `Atualizar Anamnese e Exame Físico`

### Step 3: Simplify Breadcrumb Navigation

- [ ] **Breadcrumb** (Lines 68-83): Remove conditional logic, keep only edit-specific breadcrumb:

  ```django
  <li class="breadcrumb-item">
    <a href="{% url 'patients:patient_events_timeline' patient_id=form.instance.patient.pk %}">
      {{ form.instance.patient.name }} - Timeline
    </a>
  </li>
  <li class="breadcrumb-item">
    <a href="{% url 'historyandphysicals:historyandphysical_detail' pk=form.instance.pk %}">
      Anamnese e Exame Físico
    </a>
  </li>
  <li class="breadcrumb-item active" aria-current="page">Editar</li>
  ```

### Step 4: Simplify Navigation Buttons

- [ ] **Header Buttons** (Lines 96-113): Remove conditional logic, keep only edit-specific buttons:

  ```django
  <a href="{% url 'historyandphysicals:historyandphysical_detail' pk=form.instance.pk %}" class="btn btn-outline-secondary me-2">
    <i class="bi bi-eye me-1"></i>
    Ver Detalhes
  </a>
  <a href="{% url 'patients:patient_events_timeline' patient_id=form.instance.patient.pk %}" class="btn btn-outline-secondary">
    <i class="bi bi-arrow-left me-1"></i>
    Voltar
  </a>
  ```

### Step 5: Simplify Cancel Button Logic

- [ ] **Cancel Button** (Lines 224-233): Remove conditional logic, keep only edit-specific behavior:

  ```django
  <a href="{% url 'patients:patient_events_timeline' patient_id=form.instance.patient.pk %}" class="btn btn-outline-secondary ms-2">
    <i class="bi bi-x-circle me-1"></i>
    Cancelar
  </a>
  ```

### Step 6: Keep Edit-Specific Features

- [ ] **Keep Delete Button** (Lines 235-242): This should remain as it's edit-specific functionality
- [ ] **Keep "Ver Detalhes" button**: This is edit-specific and should remain

### Step 7: Update View References

- [ ] Update all Django views that reference this template
- [ ] Update any URL patterns or view names if necessary
- [ ] Update any include statements or template references

## Expected Outcome

After cleanup, the template will be:

1. **Simplified**: No more conditional logic for unused create scenarios
2. **Focused**: Dedicated specifically to editing existing historyandphysicals
3. **Maintainable**: Clearer purpose and reduced complexity
4. **Consistent**: Follows single-responsibility principle

## Files to Update After Cleanup

- Views in `apps/historyandphysicals/views.py`
- URL patterns in `apps/historyandphysicals/urls.py`
- Any other templates that reference this template

