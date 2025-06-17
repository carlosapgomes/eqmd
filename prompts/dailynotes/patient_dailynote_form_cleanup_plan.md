# Patient DailyNote Form Template Cleanup Plan

## Template: `patient_dailynote_form.html`
**Current Purpose**: Used only to create a new dailynote for a specific patient
**File Location**: `apps/dailynotes/templates/dailynotes/patient_dailynote_form.html`

## Analysis
The current template contains remnants of conditional logic and some elements that might be designed for editing scenarios. Since this template is used **only for creating new dailynotes**, any edit-related code can be removed and creation-specific elements should be streamlined.

## Step-by-Step Cleanup Plan

### 1. Update Page Title Block
- **Current**: Line 4 has conditional logic `{% if form.instance.pk %}Editar{% else %}Nova{% endif %}`
- **Action**: Simplify to just "Nova Evolução - {{ patient.name }}"
- **Lines to modify**: 4

### 2. Remove Unnecessary Container Wrapper
- **Current**: Lines 82-84 and 230-232 have unnecessary container-fluid wrapper
- **Action**: Remove the extra container div structure, keep only the essential card layout
- **Lines to modify**: 82-84, 230-232

### 3. Verify Patient Hidden Field
- **Current**: Line 112 has hidden patient field (correct for creation)
- **Action**: Keep as-is, this is correct for patient-specific creation
- **Lines to modify**: None needed

### 4. Clean Up Form Actions
- **Current**: Lines 183-193 have simplified create-only actions
- **Action**: Verify button text is creation-specific ("Salvar Evolução") - already correct
- **Lines to modify**: None needed (already clean)

### 5. Remove Edit-Related Help Text
- **Current**: No edit-specific help text found
- **Action**: Verify all help text is creation-appropriate
- **Lines to modify**: None needed

### 6. Optimize JavaScript Placeholder
- **Current**: Line 248 has generic placeholder "Conteúdo da evolução..."
- **Action**: Make it more creation-specific: "Digite o conteúdo da nova evolução..."
- **Lines to modify**: 248

### 7. Remove Auto-save Logic (if present)
- **Current**: Lines 280-288 have auto-save functionality
- **Action**: Consider removing auto-save for new records (optional, may keep for user experience)
- **Lines to modify**: 280-288 (optional removal)

### 8. Verify Breadcrumb Links
- **Current**: Lines 60-66 have patient timeline breadcrumb
- **Action**: Ensure all links are appropriate for creation context - already correct
- **Lines to modify**: None needed

### 9. Clean Up Sample Content Integration
- **Current**: Lines 155-160 and 186-191 handle sample content templates
- **Action**: Verify this integration is appropriate for creation - keep as-is
- **Lines to modify**: None needed

### 10. Remove Unnecessary CSS Classes
- **Current**: Check for any edit-specific CSS classes
- **Action**: Verify all CSS is creation-appropriate
- **Lines to modify**: Review and clean if needed

## Expected Benefits
1. **Focused functionality**: Template clearly serves only creation purpose
2. **Simplified codebase**: Removes any ambiguous conditional logic
3. **Better user experience**: Creation-specific language and flow
4. **Reduced maintenance**: Single-purpose template is easier to maintain

## Validation Steps
1. Test new dailynote creation for patients
2. Verify patient context is properly maintained
3. Ensure sample content integration works
4. Test form validation and error handling
5. Confirm breadcrumb navigation works correctly

## Risk Assessment
- **Low Risk**: Template is creation-only, removing edit remnants won't break functionality
- **User Experience**: Ensure creation flow remains smooth and intuitive
- **Integration**: Verify patient context and timeline integration remain intact