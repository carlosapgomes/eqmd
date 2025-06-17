# DailyNote Form Template Cleanup Plan

## Template: `dailynote_form.html`
**Current Purpose**: Used only to edit/update an existing dailynote
**File Location**: `apps/dailynotes/templates/dailynotes/dailynote_form.html`

## Analysis
The current template contains conditional logic (`{% if form.instance.pk %}`) throughout to handle both creation and editing scenarios. Since this template is now used **only for editing**, all creation-related code can be removed.

## Step-by-Step Cleanup Plan

### 1. Update Page Title Block
- **Current**: Lines 4-10 with conditional title logic
- **Action**: Remove conditional logic, keep only "Editar Evolução - {{ form.instance.patient.name }}"
- **Lines to modify**: 4-10

### 2. Clean Up Breadcrumb Navigation
- **Current**: Lines 67-82 with conditional breadcrumb logic
- **Action**: Remove `{% else %}` branch (lines 79-80), keep only the editing breadcrumb path
- **Lines to modify**: 67-82

### 3. Simplify Main Header
- **Current**: Lines 88-93 with conditional header text
- **Action**: Remove conditional logic, keep only "Editar Evolução"
- **Lines to modify**: 88-93

### 4. Clean Up Header Toolbar
- **Current**: Lines 95-112 with conditional back button logic
- **Action**: Remove `{% else %}` branch (lines 106-111), keep only the patient timeline link
- **Lines to modify**: 95-112

### 5. Simplify Card Title
- **Current**: Lines 120-125 with conditional card title
- **Action**: Remove conditional logic, keep only "Editar Informações da Evolução"
- **Lines to modify**: 120-125

### 6. Clean Up Form Actions
- **Current**: Lines 214-232 with conditional button text and actions
- **Action**: 
  - Remove conditional logic in button text (lines 216-220), keep only "Atualizar Evolução"
  - Remove `{% else %}` branch for cancel button (lines 227-231)
  - Keep the delete button section (lines 234-241) as it's edit-specific
- **Lines to modify**: 214-232

### 7. Remove Create-Related CSS/JS (if any)
- **Current**: No specific create-only styles identified
- **Action**: No changes needed in CSS/JS sections

## Expected Benefits
1. **Reduced complexity**: Eliminates unnecessary conditional logic
2. **Improved maintainability**: Template purpose is clear and focused
3. **Better performance**: Fewer template conditionals to evaluate
4. **Cleaner code**: Removes dead code paths that are never executed

## Validation Steps
1. Verify the template is only used in edit views (not create views)
2. Test that all links and buttons work correctly after cleanup
3. Ensure breadcrumb navigation remains functional
4. Confirm delete functionality is preserved

## Risk Assessment
- **Low Risk**: Template is only used for editing, so removing create logic won't break functionality
- **Testing Required**: Verify all edit-related features work correctly