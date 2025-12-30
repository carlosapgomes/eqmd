# Linked Fields with Data Sources - Implementation Plan

**Feature**: Dropdown that fills multiple related fields (e.g., procedure name and code)
**Date**: 2025-10-17
**Status**: Planning Phase

## Overview

Implement a system where selecting a value in one dropdown can automatically populate related fields, enabling scenarios like:

- Select procedure name → auto-fill procedure code
- Select diagnosis → auto-fill ICD code
- Select medication → auto-fill dosage and administration route

## Design Principles

1. **Backward Compatibility**: Existing forms continue to work without modification
2. **Opt-in Feature**: Only applies when `data_source` is configured
3. **No Overengineering**: Simple, maintainable implementation
4. **Progressive Enhancement**: Works without JavaScript (manual entry), enhanced with JavaScript

## Architecture Overview

### Data Structure

```json
{
  "sections": { /* existing sections config */ },
  "fields": {
    "procedure_name": {
      "type": "choice",
      "label": "Nome do Procedimento",
      "x": 4.5, "y": 10.0, "width": 8.0, "height": 0.7,
      "data_source": "procedures",           // NEW: link to data source
      "data_source_key": "name",             // NEW: which field to use
      "required": true
    },
    "procedure_code": {
      "type": "text",
      "label": "Código do Procedimento",
      "x": 13.0, "y": 10.0, "width": 4.0, "height": 0.7,
      "data_source": "procedures",           // NEW: same data source
      "data_source_key": "code",             // NEW: which field to use
      "linked_readonly": true,               // NEW: readonly when filled via link
      "required": true
    }
  },
  "data_sources": {                          // NEW: centralized data
    "procedures": [
      {"name": "Apendicectomia", "code": "0409010018"},
      {"name": "Colecistectomia", "code": "0408010036"},
      {"name": "Hérnia inguinal", "code": "0409030059"}
    ]
  }
}
```

## Implementation Steps

### Phase 1: Backend Infrastructure (No Breaking Changes)

#### Step 1.1: Update Field Configuration Model

**File**: `apps/pdf_forms/models.py`

**Changes**:

- No model changes needed (JSONField already supports nested structures)
- Add property method to check if template uses data sources

**Code**:

```python
@property
def has_data_sources(self):
    """Check if template configuration includes data sources."""
    if not self.form_fields:
        return False
    return 'data_sources' in self.form_fields
```

**Testing**:

- Existing templates continue to work
- New property returns False for legacy configs

---

#### Step 1.2: Add Data Source Validation

**File**: `apps/pdf_forms/security.py`

**Changes**:

- Add validation for `data_sources` structure
- Add validation for `data_source` and `data_source_key` in fields
- Ensure data source references are valid

**Code**:

```python
@staticmethod
def validate_data_sources(data_sources):
    """
    Validate data sources configuration.

    Args:
        data_sources (dict): Data sources configuration

    Raises:
        ValidationError: If configuration is invalid
    """
    if not isinstance(data_sources, dict):
        raise ValidationError("data_sources must be a dictionary")

    for source_name, source_data in data_sources.items():
        # Validate source name
        if not isinstance(source_name, str) or not source_name:
            raise ValidationError(f"Invalid data source name: {source_name}")

        # Validate source data is a list
        if not isinstance(source_data, list):
            raise ValidationError(f"Data source '{source_name}' must be a list")

        # Validate each item is a dictionary
        for idx, item in enumerate(source_data):
            if not isinstance(item, dict):
                raise ValidationError(
                    f"Item {idx} in data source '{source_name}' must be a dictionary"
                )

            # Validate item has at least one key
            if not item:
                raise ValidationError(
                    f"Item {idx} in data source '{source_name}' cannot be empty"
                )

@staticmethod
def validate_field_data_source_reference(field_name, field_config, available_sources):
    """
    Validate that field's data source reference is valid.

    Args:
        field_name (str): Name of the field
        field_config (dict): Field configuration
        available_sources (dict): Available data sources

    Raises:
        ValidationError: If reference is invalid
    """
    data_source = field_config.get('data_source')
    data_source_key = field_config.get('data_source_key')

    # Both or neither must be present
    if bool(data_source) != bool(data_source_key):
        raise ValidationError(
            f"Field '{field_name}': both 'data_source' and 'data_source_key' "
            f"must be specified together"
        )

    # If present, validate
    if data_source:
        # Check source exists
        if data_source not in available_sources:
            raise ValidationError(
                f"Field '{field_name}': data source '{data_source}' not found. "
                f"Available: {list(available_sources.keys())}"
            )

        # Check key exists in at least one item
        source_items = available_sources[data_source]
        if source_items:
            first_item = source_items[0]
            if data_source_key not in first_item:
                raise ValidationError(
                    f"Field '{field_name}': key '{data_source_key}' not found in "
                    f"data source '{data_source}'. Available keys: {list(first_item.keys())}"
                )
```

**Update `validate_field_configuration` method**:

```python
@staticmethod
def validate_field_configuration(field_config):
    """Enhanced to validate data sources."""
    # Existing validation...

    # NEW: Validate data sources if present
    data_sources = field_config.get('data_sources', {})
    if data_sources:
        PDFFormSecurity.validate_data_sources(data_sources)

    # Extract fields (handle both sectioned and legacy formats)
    fields = field_config.get('fields', field_config)

    # NEW: Validate field data source references
    for field_name, config in fields.items():
        if isinstance(config, dict) and 'data_source' in config:
            PDFFormSecurity.validate_field_data_source_reference(
                field_name, config, data_sources
            )

    # Existing validation continues...
```

**Testing**:

- Valid data sources pass validation
- Invalid structures raise clear errors
- Fields with invalid source references are caught
- Existing configs without data sources pass validation

---

#### Step 1.3: Add Data Source Utilities

**File**: `apps/pdf_forms/services/data_source_utils.py` (NEW FILE)

**Purpose**: Helper functions for working with data sources

**Code**:

```python
"""
Utilities for managing PDF form data sources.
Supports linked field functionality.
"""


class DataSourceUtils:
    """Utilities for working with form data sources."""

    @staticmethod
    def get_data_source(form_config, source_name):
        """
        Get a data source by name.

        Args:
            form_config (dict): Complete form configuration
            source_name (str): Name of the data source

        Returns:
            list: Data source items or empty list if not found
        """
        if not isinstance(form_config, dict):
            return []

        data_sources = form_config.get('data_sources', {})
        return data_sources.get(source_name, [])

    @staticmethod
    def get_field_choices_from_source(form_config, field_config):
        """
        Generate field choices from a data source.

        Args:
            form_config (dict): Complete form configuration
            field_config (dict): Field configuration

        Returns:
            list: List of choices for the field, or None if not using data source
        """
        data_source = field_config.get('data_source')
        data_source_key = field_config.get('data_source_key')

        if not data_source or not data_source_key:
            return None

        # Get the data source
        source_items = DataSourceUtils.get_data_source(form_config, data_source)

        # Extract unique values for this key
        choices = []
        seen = set()
        for item in source_items:
            value = item.get(data_source_key)
            if value is not None and value not in seen:
                choices.append(value)
                seen.add(value)

        return choices

    @staticmethod
    def get_linked_fields(form_config, data_source_name):
        """
        Get all fields linked to a specific data source.

        Args:
            form_config (dict): Complete form configuration
            data_source_name (str): Name of the data source

        Returns:
            dict: Field names mapped to their data_source_key
        """
        # Extract fields from config (handle both formats)
        fields = form_config.get('fields', form_config)

        linked = {}
        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                continue

            if field_config.get('data_source') == data_source_name:
                key = field_config.get('data_source_key')
                if key:
                    linked[field_name] = key

        return linked

    @staticmethod
    def get_data_source_item_by_value(source_items, key, value):
        """
        Find a data source item by a specific key-value pair.

        Args:
            source_items (list): List of data source items
            key (str): Key to match
            value: Value to match

        Returns:
            dict: Matching item or None if not found
        """
        for item in source_items:
            if item.get(key) == value:
                return item
        return None

    @staticmethod
    def build_linked_fields_map(form_config):
        """
        Build a complete map of data sources and their linked fields.
        Used for frontend JavaScript initialization.

        Args:
            form_config (dict): Complete form configuration

        Returns:
            dict: Map of data sources with field linkages
        """
        data_sources = form_config.get('data_sources', {})
        if not data_sources:
            return {}

        linked_map = {}

        for source_name in data_sources.keys():
            linked_fields = DataSourceUtils.get_linked_fields(form_config, source_name)

            if linked_fields:
                linked_map[source_name] = {
                    'fields': linked_fields,
                    'data': data_sources[source_name]
                }

        return linked_map
```

**Testing**:

- Test extracting data sources
- Test generating field choices
- Test finding linked fields
- Test building linked fields map

---

### Phase 2: Form Generation Enhancement

#### Step 2.1: Update Form Generator

**File**: `apps/pdf_forms/services/form_generator.py`

**Changes**:

- Detect when a choice field uses a data source
- Auto-generate choices from data source
- Add metadata for JavaScript to use

**Code** (modify `generate_form_class` method):

```python
def generate_form_class(self, pdf_template, patient=None):
    """Enhanced to handle data sources."""
    form_fields = {}
    field_config = pdf_template.form_fields or {}
    initial_values = {}

    # ... existing code ...

    # NEW: Store data source metadata on form class
    if 'data_sources' in field_config:
        form_class._linked_fields_map = DataSourceUtils.build_linked_fields_map(
            field_config
        )
    else:
        form_class._linked_fields_map = {}

    return form_class
```

**Code** (modify `_create_django_field` method):

```python
def _create_django_field(self, field_name, config, form_config=None):
    """Enhanced to handle data source choices."""
    field_type = config.get('type', 'text')

    # NEW: For choice fields, check if using data source
    if field_type == 'choice' and form_config:
        data_source_choices = DataSourceUtils.get_field_choices_from_source(
            form_config, config
        )
        if data_source_choices:
            # Override config choices with data source choices
            config = config.copy()
            config['choices'] = data_source_choices

    # Existing field creation logic...

    # NEW: Add data attributes for linked fields
    if config.get('data_source'):
        widget_attrs = field_kwargs.get('widget', forms.TextInput()).attrs
        widget_attrs['data-source'] = config['data_source']
        widget_attrs['data-source-key'] = config['data_source_key']

        if config.get('linked_readonly'):
            widget_attrs['data-linked-readonly'] = 'true'

    return field_class(**field_kwargs)
```

**Testing**:

- Choice fields with data sources get correct choices
- Linked fields get correct data attributes
- Non-data-source fields work as before

---

### Phase 2.5: Admin Interface for Data Sources

**Goal**: Add data source management to the existing visual field configurator

#### Step 2.5.1: Add Data Source Management Panel

**File**: `apps/pdf_forms/templates/admin/pdf_forms/pdfformtemplate/configure_fields.html`

**Changes**: Add a new "Data Sources" section to the properties panel (after sections management)

**Code** (add after line 874 `</div><!-- #section-management -->`):

```html
<!-- Data Source Management Panel -->
<div id="data-source-management" class="mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4>Data Sources</h4>
        <button type="button" class="btn btn-outline-success btn-sm" id="add-data-source-btn">
            <i class="bi bi-plus"></i> Add Data Source
        </button>
    </div>
    <div id="data-sources-list" class="mb-3">
        <div style="padding: 15px; text-align: center; color: #666; font-style: italic;">
            No data sources configured
        </div>
    </div>
    <div class="section-controls">
        <button type="button" class="btn btn-outline-info btn-sm" id="preview-data-sources-btn">
            <i class="bi bi-table"></i> Preview Data
        </button>
    </div>
</div>
```

**CSS** (add to existing `<style>` block):

```css
/* Data Source Management Styles */
#data-source-management {
    border-top: 1px solid #ddd;
    padding-top: 15px;
}

.data-source-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    margin-bottom: 8px;
    background: #f8f9fa;
    transition: all 0.2s ease;
}

.data-source-item:hover {
    background: #e9ecef;
    border-color: #28a745;
}

.data-source-info {
    flex: 1;
}

.data-source-name {
    font-weight: bold;
    color: #495057;
    margin-right: 8px;
}

.data-source-count {
    font-size: 11px;
    color: #6c757d;
    background: #e9ecef;
    padding: 2px 6px;
    border-radius: 10px;
    margin-left: 8px;
}

.data-source-actions {
    display: flex;
    gap: 5px;
}

.data-source-actions button {
    padding: 4px 8px;
    font-size: 11px;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.data-item-row {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    padding: 8px;
    background: #f8f9fa;
    border-radius: 4px;
}

.data-item-row input {
    flex: 1;
    padding: 6px;
    border: 1px solid #ddd;
    border-radius: 3px;
    font-size: 12px;
}

.data-item-row button {
    padding: 6px 10px;
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
}

.data-item-row button:hover {
    background: #c82333;
}
```

**Testing**:

- Panel renders correctly in configurator
- Styling integrates with existing UI

---

#### Step 2.5.2: Add Data Source Editor Modal

**File**: Same as above

**Code** (add after the `#sectionPreviewModal` div, around line 1100):

```html
<!-- Data Source Editor Modal -->
<div class="modal fade" id="dataSourceModal" tabindex="-1" aria-labelledby="dataSourceModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="dataSourceModalLabel">Data Source Configuration</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <form id="data-source-form">
                    <div class="mb-3">
                        <label for="data-source-name" class="form-label">Data Source Name</label>
                        <input type="text" class="form-control" id="data-source-name" required>
                        <div class="form-text">Unique identifier (e.g., procedures, diagnoses). Only letters, numbers, and underscores.</div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Data Items</label>
                        <div class="form-text mb-2">
                            Add rows with key-value pairs. The first item defines the keys for all items.
                        </div>
                        <div id="data-items-container">
                            <!-- Data items will be dynamically added here -->
                        </div>
                        <button type="button" class="btn btn-sm btn-secondary mt-2" id="add-data-item-btn">
                            <i class="bi bi-plus"></i> Add Item
                        </button>
                    </div>

                    <div class="alert alert-info">
                        <strong>💡 Tip:</strong> First item defines the structure. All items must have the same keys.
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" id="save-data-source-btn">Save Data Source</button>
            </div>
        </div>
    </div>
</div>

<!-- Data Source Preview Modal -->
<div class="modal fade" id="dataSourcePreviewModal" tabindex="-1" aria-labelledby="dataSourcePreviewModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="dataSourcePreviewModalLabel">Data Sources Preview</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <div id="data-source-preview-content">
                    <!-- Preview content will be populated here -->
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
```

**Testing**:

- Modals open/close correctly
- Form validation works
- Data persists when editing

---

#### Step 2.5.3: Add JavaScript for Data Source Management

**File**: Same as above

**Code** (add to existing `<script>` section, after section management functions):

```javascript
// Data Source Management Variables
let dataSources = {};
let editingDataSourceName = null;

// Data Source Management Functions
function loadExistingDataSources() {
    // Extract data sources from existing config if present
    const existingConfig = {{ current_fields_json|safe }};
    if (existingConfig && existingConfig.data_sources) {
        dataSources = existingConfig.data_sources;
        updateDataSourcesList();
    }
}

function updateDataSourcesList() {
    const dataSourcesList = document.getElementById('data-sources-list');

    if (Object.keys(dataSources).length === 0) {
        dataSourcesList.innerHTML = '<div style="padding: 15px; text-align: center; color: #666; font-style: italic;">No data sources configured</div>';
        return;
    }

    dataSourcesList.innerHTML = '';

    Object.entries(dataSources).forEach(([sourceName, sourceData]) => {
        const dataSourceItem = document.createElement('div');
        dataSourceItem.className = 'data-source-item';
        dataSourceItem.setAttribute('data-source-name', sourceName);

        const itemCount = Array.isArray(sourceData) ? sourceData.length : 0;
        const keys = itemCount > 0 && sourceData[0] ? Object.keys(sourceData[0]).join(', ') : 'N/A';

        dataSourceItem.innerHTML = `
            <div class="data-source-info">
                <span class="data-source-name">${sourceName}</span>
                <span class="data-source-count">${itemCount} items</span>
                <div style="font-size: 10px; color: #999;">Keys: ${keys}</div>
            </div>
            <div class="data-source-actions">
                <button class="btn-edit" onclick="editDataSource('${sourceName}')">Edit</button>
                <button class="btn-delete" onclick="deleteDataSource('${sourceName}')">Delete</button>
            </div>
        `;

        dataSourcesList.appendChild(dataSourceItem);
    });
}

function showDataSourceModal(sourceName = null) {
    editingDataSourceName = sourceName;
    const modal = document.getElementById('dataSourceModal');
    const modalTitle = document.getElementById('dataSourceModalLabel');

    if (sourceName) {
        // Editing existing data source
        modalTitle.textContent = 'Edit Data Source';
        const sourceData = dataSources[sourceName];

        document.getElementById('data-source-name').value = sourceName;
        document.getElementById('data-source-name').disabled = true;

        // Load existing data items
        loadDataItems(sourceData);
    } else {
        // Creating new data source
        modalTitle.textContent = 'Add New Data Source';
        document.getElementById('data-source-form').reset();
        document.getElementById('data-source-name').disabled = false;

        // Start with empty data items container
        document.getElementById('data-items-container').innerHTML = '';
        addDataItem(); // Add first empty item
    }

    showModal(modal);
}

function loadDataItems(sourceData) {
    const container = document.getElementById('data-items-container');
    container.innerHTML = '';

    if (!Array.isArray(sourceData) || sourceData.length === 0) {
        addDataItem();
        return;
    }

    // Get keys from first item
    const keys = Object.keys(sourceData[0]);

    sourceData.forEach((item, index) => {
        addDataItemRow(keys, item, index);
    });
}

function addDataItem() {
    const container = document.getElementById('data-items-container');
    const existingItems = container.querySelectorAll('.data-item-row');

    let keys = [];
    if (existingItems.length > 0) {
        // Get keys from first item
        const firstItem = existingItems[0];
        keys = Array.from(firstItem.querySelectorAll('input')).map(input => input.placeholder || input.dataset.key);
    } else {
        // First item - ask for keys
        showAddKeysDialog();
        return;
    }

    addDataItemRow(keys, {}, existingItems.length);
}

function showAddKeysDialog() {
    const keys = prompt('Enter keys for data items (comma-separated):\nExample: name, code');

    if (!keys) return;

    const keyArray = keys.split(',').map(k => k.trim()).filter(k => k);

    if (keyArray.length === 0) {
        showError('Please enter at least one key');
        return;
    }

    addDataItemRow(keyArray, {}, 0);
}

function addDataItemRow(keys, values = {}, index) {
    const container = document.getElementById('data-items-container');
    const row = document.createElement('div');
    row.className = 'data-item-row';
    row.dataset.index = index;

    let inputsHtml = keys.map(key => {
        const value = values[key] || '';
        return `<input type="text" placeholder="${key}" data-key="${key}" value="${value}">`;
    }).join('');

    row.innerHTML = `
        ${inputsHtml}
        <button type="button" onclick="removeDataItemRow(this)">×</button>
    `;

    container.appendChild(row);
}

function removeDataItemRow(button) {
    button.parentElement.remove();
}

function saveDataSourceConfiguration() {
    const sourceName = document.getElementById('data-source-name').value.trim();

    // Validation
    if (!sourceName) {
        showError('Data source name is required');
        return;
    }

    // Validate source name format
    if (!/^[a-zA-Z0-9_]+$/.test(sourceName)) {
        showError('Data source name can only contain letters, numbers, and underscores');
        return;
    }

    // Check for duplicate names (when creating new)
    if (!editingDataSourceName && dataSources[sourceName]) {
        showError('Data source name already exists');
        return;
    }

    // Collect data items
    const container = document.getElementById('data-items-container');
    const rows = container.querySelectorAll('.data-item-row');

    if (rows.length === 0) {
        showError('Please add at least one data item');
        return;
    }

    // Get keys from first row
    const firstRow = rows[0];
    const keys = Array.from(firstRow.querySelectorAll('input')).map(input => input.dataset.key);

    // Collect all items
    const items = [];
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        const item = {};
        inputs.forEach((input, i) => {
            const key = keys[i];
            const value = input.value.trim();
            if (value) {
                item[key] = value;
            }
        });

        // Only add non-empty items
        if (Object.keys(item).length > 0) {
            items.push(item);
        }
    });

    if (items.length === 0) {
        showError('Please fill in at least one complete data item');
        return;
    }

    // Validate all items have the same keys
    const expectedKeys = JSON.stringify(keys.sort());
    for (let i = 0; i < items.length; i++) {
        const itemKeys = JSON.stringify(Object.keys(items[i]).sort());
        if (itemKeys !== expectedKeys) {
            showError(`Item ${i + 1} has inconsistent keys. All items must have the same keys: ${keys.join(', ')}`);
            return;
        }
    }

    // Save data source
    dataSources[sourceName] = items;

    // Update UI
    updateDataSourcesList();
    updateFieldAutoFillOptions(); // Update the auto-fill dropdown with new data source

    // Close modal
    const modal = document.getElementById('dataSourceModal');
    closeModal(modal);
    editingDataSourceName = null;

    showSuccess(`Data source "${sourceName}" ${editingDataSourceName ? 'updated' : 'created'} successfully`);
}

function editDataSource(sourceName) {
    showDataSourceModal(sourceName);
}

function deleteDataSource(sourceName) {
    // Check if any fields are using this data source
    const fieldsUsingSource = Object.entries(fields).filter(([, fieldConfig]) =>
        fieldConfig.data_source === sourceName
    );

    let message = `Delete data source "${sourceName}"?`;
    if (fieldsUsingSource.length > 0) {
        message += `\n\nWarning: ${fieldsUsingSource.length} field(s) are currently using this data source:\n`;
        message += fieldsUsingSource.map(([name]) => `  - ${name}`).join('\n');
        message += '\n\nThese fields will lose their data source linkage.';
    }

    if (!confirm(message)) {
        return;
    }

    // Remove data source references from fields
    fieldsUsingSource.forEach(([fieldName]) => {
        delete fields[fieldName].data_source;
        delete fields[fieldName].data_source_key;
        delete fields[fieldName].linked_readonly;
    });

    // Delete data source
    delete dataSources[sourceName];

    // Update UI
    updateDataSourcesList();
    updateFieldList();

    showSuccess(`Data source "${sourceName}" deleted successfully`);
}

function showDataSourcePreview() {
    const modal = document.getElementById('dataSourcePreviewModal');
    const previewContent = document.getElementById('data-source-preview-content');

    previewContent.innerHTML = '';

    if (Object.keys(dataSources).length === 0) {
        previewContent.innerHTML = '<div class="text-center text-muted p-4">No data sources configured</div>';
    } else {
        Object.entries(dataSources).forEach(([sourceName, sourceData]) => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'mb-4';

            const keys = sourceData.length > 0 ? Object.keys(sourceData[0]) : [];

            let tableHtml = `
                <h5>${sourceName} <span class="badge bg-primary">${sourceData.length} items</span></h5>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr>${keys.map(k => `<th>${k}</th>`).join('')}</tr>
                        </thead>
                        <tbody>
            `;

            sourceData.forEach(item => {
                tableHtml += '<tr>';
                keys.forEach(key => {
                    tableHtml += `<td>${item[key] || '-'}</td>`;
                });
                tableHtml += '</tr>';
            });

            tableHtml += `
                        </tbody>
                    </table>
                </div>
            `;

            sourceDiv.innerHTML = tableHtml;
            previewContent.appendChild(sourceDiv);
        });
    }

    showModal(modal);
}

function updateFieldAutoFillOptions() {
    // This function would need backend integration to add data source options
    // to the auto-fill dropdown. For now, we'll just update the field properties
    // when a field is selected to show if it's linked to a data source

    // Update field properties panel to show data source options
    if (selectedField && fields[selectedField]) {
        const field = fields[selectedField];
        if (field.data_source) {
            // Visual indicator that field is linked
            updateFieldList();
        }
    }
}

// Update saveFields function to include data sources
const originalSaveFields = saveFields;
saveFields = function() {
    const templateId = '{{ template.id }}';
    const apiUrl = `../api/save-fields/`;

    // Show loading state
    const saveBtn = document.getElementById('save-fields-btn');
    const originalText = saveBtn.textContent;
    saveBtn.textContent = 'Saving...';
    saveBtn.disabled = true;

    // Build configuration object
    let configToSave = {};

    if (Object.keys(dataSources).length > 0) {
        configToSave.data_sources = dataSources;
    }

    if (Object.keys(sections).length > 0) {
        configToSave.sections = sections;
        configToSave.fields = fields;
    } else {
        // Legacy format compatibility
        if (Object.keys(dataSources).length > 0) {
            configToSave.fields = fields;
        } else {
            configToSave = fields;
        }
    }

    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            fields: configToSave
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
        } else {
            showError(data.error);
        }
    })
    .catch(error => {
        showError('Error saving fields: ' + error.message);
    })
    .finally(() => {
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
    });
};

// Update setupEventListeners to include data source buttons
const originalSetupEventListeners = setupEventListeners;
setupEventListeners = function() {
    originalSetupEventListeners();

    // Data source management event listeners
    document.getElementById('add-data-source-btn').addEventListener('click', () => showDataSourceModal());
    document.getElementById('save-data-source-btn').addEventListener('click', saveDataSourceConfiguration);
    document.getElementById('preview-data-sources-btn').addEventListener('click', showDataSourcePreview);
    document.getElementById('add-data-item-btn').addEventListener('click', addDataItem);
};

// Load data sources on init
document.addEventListener('DOMContentLoaded', function() {
    loadExistingDataSources();
});
```

**Testing**:

- Data sources can be created, edited, deleted
- Data items management works correctly
- Validation prevents invalid configurations
- Preview shows data in table format

---

#### Step 2.5.4: Enhance Field Properties Panel for Data Source Linking

**File**: Same as above

**Code** (update the field properties form section around line 961):

```html
<!-- Add after the auto-fill dropdown, before font size -->
<div class="form-group" id="data-source-link-group" style="display: none;">
    <label>Link to Data Source</label>
    <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
        <strong>💡 Data Source Linking</strong>
        <div style="font-size: 11px; margin-top: 5px;">
            Link this field to a data source to enable automatic population of related fields.
        </div>
    </div>

    <div class="mb-2">
        <label for="field-data-source">Data Source</label>
        <select id="field-data-source" name="data_source" class="form-control">
            <option value="">-- None --</option>
            <!-- Populated dynamically with available data sources -->
        </select>
    </div>

    <div class="mb-2" id="data-source-key-group" style="display: none;">
        <label for="field-data-source-key">Data Source Key</label>
        <select id="field-data-source-key" name="data_source_key" class="form-control">
            <option value="">-- Select Key --</option>
            <!-- Populated dynamically based on selected data source -->
        </select>
    </div>

    <div class="mb-2">
        <label>
            <input type="checkbox" id="field-linked-readonly" name="linked_readonly">
            Make read-only when auto-filled
        </label>
        <div style="font-size: 11px; color: #666;">
            Prevents manual editing of auto-filled values
        </div>
    </div>
</div>
```

**JavaScript** (add to field properties functions):

```javascript
// Update handleFieldTypeChange to show/hide data source linking
function handleFieldTypeChange() {
    const fieldType = document.getElementById('field-type').value;

    // Existing code...

    // Show data source linking for choice fields
    const dataSourceLinkGroup = document.getElementById('data-source-link-group');
    if (fieldType === 'choice' && Object.keys(dataSources).length > 0) {
        dataSourceLinkGroup.style.display = 'block';
        updateDataSourceDropdown();
    } else {
        dataSourceLinkGroup.style.display = 'none';
    }

    // Also show for text fields that might be auto-filled
    if (['text', 'number', 'date'].includes(fieldType) && Object.keys(dataSources).length > 0) {
        dataSourceLinkGroup.style.display = 'block';
        updateDataSourceDropdown();
    }
}

function updateDataSourceDropdown() {
    const select = document.getElementById('field-data-source');

    // Clear existing options except first
    const firstOption = select.firstElementChild;
    select.innerHTML = '';
    select.appendChild(firstOption);

    // Add data source options
    Object.keys(dataSources).forEach(sourceName => {
        const option = document.createElement('option');
        option.value = sourceName;
        option.textContent = sourceName;
        select.appendChild(option);
    });
}

// Handle data source selection change
document.getElementById('field-data-source').addEventListener('change', function() {
    const sourceName = this.value;
    const keyGroup = document.getElementById('data-source-key-group');
    const keySelect = document.getElementById('field-data-source-key');

    if (sourceName && dataSources[sourceName]) {
        // Show key selection
        keyGroup.style.display = 'block';

        // Populate keys from first item
        const firstItem = dataSources[sourceName][0];
        if (firstItem) {
            const keys = Object.keys(firstItem);

            // Clear existing options
            keySelect.innerHTML = '<option value="">-- Select Key --</option>';

            keys.forEach(key => {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = key;
                keySelect.appendChild(option);
            });
        }
    } else {
        keyGroup.style.display = 'none';
    }

    updateSelectedField();
});

// Handle data source key selection
document.getElementById('field-data-source-key').addEventListener('change', updateSelectedField);
document.getElementById('field-linked-readonly').addEventListener('change', updateSelectedField);

// Update loadFieldProperties to load data source settings
function loadFieldProperties(fieldName) {
    const fieldConfig = fields[fieldName];

    // Existing code...

    // Load data source settings
    document.getElementById('field-data-source').value = fieldConfig.data_source || '';
    document.getElementById('field-data-source-key').value = fieldConfig.data_source_key || '';
    document.getElementById('field-linked-readonly').checked = fieldConfig.linked_readonly || false;

    // Trigger data source change to show key dropdown if needed
    if (fieldConfig.data_source) {
        document.getElementById('field-data-source').dispatchEvent(new Event('change'));
    }

    handleFieldTypeChange();
}

// Update updateSelectedField to save data source settings
function updateSelectedField() {
    if (!selectedField) return;

    const fieldConfig = fields[selectedField];

    // Existing code...

    // Update data source settings
    const dataSource = document.getElementById('field-data-source').value;
    const dataSourceKey = document.getElementById('field-data-source-key').value;
    const linkedReadonly = document.getElementById('field-linked-readonly').checked;

    if (dataSource && dataSourceKey) {
        fieldConfig.data_source = dataSource;
        fieldConfig.data_source_key = dataSourceKey;
        fieldConfig.linked_readonly = linkedReadonly;
    } else {
        delete fieldConfig.data_source;
        delete fieldConfig.data_source_key;
        delete fieldConfig.linked_readonly;
    }

    // Rest of existing code...
}
```

**Testing**:

- Data source dropdown populates correctly
- Key dropdown shows available keys
- Field properties save/load correctly
- Visual indicators show linked fields

---

#### Step 2.5.5: Add Visual Indicators for Data Source Links

**CSS** (add to existing `<style>` block):

```css
/* Data source linked field indicators */
.field-overlay.has-data-source {
    border-color: #17a2b8;
    background: rgba(23, 162, 184, 0.1);
}

.field-overlay.has-data-source .field-label::before {
    content: "🔗 ";
    font-size: 8px;
}

.field-item.has-data-source {
    border-left: 3px solid #17a2b8;
}

.field-item.has-data-source .field-type {
    background: #d1ecf1;
    color: #0c5460;
}

.data-source-indicator {
    font-size: 10px;
    color: #17a2b8;
    font-weight: bold;
}
```

**JavaScript** (update drawField and updateFieldList functions):

```javascript
// In drawField function, add data source indicator
function drawField(fieldName, fieldConfig) {
    const overlay = document.createElement('div');
    overlay.className = 'field-overlay';
    overlay.setAttribute('data-field', fieldName);

    // Add data source mapping visual indicator
    if (fieldConfig.data_source) {
        overlay.classList.add('has-data-source');
    }

    // Existing code...
}

// In updateFieldList function, add data source indicator
function updateFieldList() {
    // Existing code...

    Object.entries(fields).forEach(([fieldName, fieldConfig]) => {
        const fieldItem = document.createElement('div');
        fieldItem.className = 'field-item';

        // Add data source indicator class
        if (fieldConfig.data_source) {
            fieldItem.classList.add('has-data-source');
        }

        // Build data source display
        let dataSourceDisplay = '';
        if (fieldConfig.data_source) {
            dataSourceDisplay = `<div class="data-source-indicator">🔗 ${fieldConfig.data_source}.${fieldConfig.data_source_key}</div>`;
        }

        fieldItem.innerHTML = `
            <div>
                <div class="field-name">${fieldConfig.label || fieldName}</div>
                <div style="font-size: 11px; color: #999;">${fieldName}</div>
                ${dataSourceDisplay}
                ${autoFillDisplay}
            </div>
            <div class="field-type">${fieldConfig.type}</div>
        `;

        // Existing code...
    });
}
```

**Testing**:

- Fields linked to data sources show visual indicators
- Overlay and list items have distinct styling
- Indicators update when linkage changes

---

### Phase 3: Frontend JavaScript Enhancement

#### Step 3.1: Create Linked Fields JavaScript

**File**: `assets/js/pdf_forms_linked_fields.js` (NEW FILE)

**Purpose**: Handle auto-fill behavior when dropdown changes

**Code**:

```javascript
/**
 * PDF Forms - Linked Fields Auto-Fill
 * Handles automatic population of related fields when using data sources
 */

(function() {
  'use strict';

  class LinkedFieldsManager {
    constructor(linkedFieldsMap) {
      this.linkedFieldsMap = linkedFieldsMap;
      this.init();
    }

    init() {
      if (!this.linkedFieldsMap || Object.keys(this.linkedFieldsMap).length === 0) {
        return; // No linked fields to manage
      }

      // Initialize all linked fields
      for (const [sourceName, sourceConfig] of Object.entries(this.linkedFieldsMap)) {
        this.initializeDataSource(sourceName, sourceConfig);
      }
    }

    initializeDataSource(sourceName, sourceConfig) {
      const fields = sourceConfig.fields;
      const data = sourceConfig.data;

      // Find the "primary" field (typically the one users interact with)
      // This is the first field in the linked group
      const fieldNames = Object.keys(fields);
      if (fieldNames.length === 0) return;

      const primaryFieldName = fieldNames[0];
      const primaryFieldKey = fields[primaryFieldName];
      const primaryField = document.querySelector(`[name="${primaryFieldName}"]`);

      if (!primaryField) return;

      // Store data on the element for quick access
      primaryField.dataset.linkedData = JSON.stringify(data);
      primaryField.dataset.linkedFields = JSON.stringify(fields);

      // Add change event listener
      primaryField.addEventListener('change', (e) => {
        this.handleFieldChange(e.target, data, fields, primaryFieldKey);
      });

      // Set initial readonly states
      this.updateReadonlyStates(fields, primaryFieldName);

      // Trigger initial population if field has value
      if (primaryField.value) {
        this.handleFieldChange(primaryField, data, fields, primaryFieldKey);
      }
    }

    handleFieldChange(primaryField, data, fields, primaryKey) {
      const selectedValue = primaryField.value;

      if (!selectedValue) {
        // Clear all linked fields
        this.clearLinkedFields(fields, primaryField.name);
        return;
      }

      // Find the matching data item
      const matchingItem = data.find(item => item[primaryKey] === selectedValue);

      if (!matchingItem) return;

      // Populate all linked fields
      for (const [fieldName, dataKey] of Object.entries(fields)) {
        if (fieldName === primaryField.name) continue; // Skip the primary field

        const targetField = document.querySelector(`[name="${fieldName}"]`);
        if (!targetField) continue;

        const value = matchingItem[dataKey];
        if (value !== undefined && value !== null) {
          targetField.value = value;

          // Trigger change event for any dependent logic
          targetField.dispatchEvent(new Event('change', { bubbles: true }));

          // Add visual feedback
          this.addVisualFeedback(targetField);
        }
      }
    }

    clearLinkedFields(fields, primaryFieldName) {
      for (const fieldName of Object.keys(fields)) {
        if (fieldName === primaryFieldName) continue;

        const targetField = document.querySelector(`[name="${fieldName}"]`);
        if (targetField && targetField.dataset.linkedReadonly === 'true') {
          targetField.value = '';
          this.removeVisualFeedback(targetField);
        }
      }
    }

    updateReadonlyStates(fields, primaryFieldName) {
      for (const fieldName of Object.keys(fields)) {
        if (fieldName === primaryFieldName) continue;

        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field && field.dataset.linkedReadonly === 'true') {
          field.setAttribute('readonly', true);
          field.classList.add('form-control-plaintext', 'bg-light');
        }
      }
    }

    addVisualFeedback(field) {
      field.classList.remove('is-invalid');
      field.classList.add('auto-filled');

      // Remove feedback after animation
      setTimeout(() => {
        field.classList.remove('auto-filled');
      }, 1000);
    }

    removeVisualFeedback(field) {
      field.classList.remove('auto-filled');
    }
  }

  // Initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', function() {
    // Check if linked fields data is available
    const linkedFieldsData = document.getElementById('linked-fields-data');

    if (linkedFieldsData) {
      try {
        const linkedFieldsMap = JSON.parse(linkedFieldsData.textContent);
        new LinkedFieldsManager(linkedFieldsMap);
      } catch (e) {
        console.error('Failed to initialize linked fields:', e);
      }
    }
  });

})();
```

**CSS** (add to relevant SCSS file):

```scss
// Visual feedback for auto-filled fields
.auto-filled {
  transition: background-color 0.5s ease;
  background-color: #d1ecf1 !important;
}

// Readonly linked fields styling
.form-control-plaintext.bg-light {
  background-color: #f8f9fa !important;
  border: 1px solid #e9ecef;
  cursor: not-allowed;
}
```

**Testing**:

- Selecting dropdown populates related fields
- Clearing dropdown clears related fields
- Readonly fields cannot be manually edited
- Visual feedback works correctly

---

#### Step 3.2: Update Form Template

**File**: `apps/pdf_forms/templates/pdf_forms/form_fill.html`

**Changes**:

- Add script tag for new JavaScript
- Add JSON data for linked fields

**Code** (add before closing `{% endblock %}`):

```django
{% block extra_js %}
{{ block.super }}

{% if form._linked_fields_map %}
<!-- Linked fields data for JavaScript -->
<script id="linked-fields-data" type="application/json">
{{ form._linked_fields_map|json_script:"linked-fields-data" }}
</script>

<!-- Linked fields functionality -->
<script src="{% static 'js/pdf_forms_linked_fields.js' %}"></script>
{% endif %}
{% endblock %}
```

**Testing**:

- Data is correctly embedded in page
- JavaScript loads only when needed
- Non-linked forms don't load extra JS

---

### Phase 4: PDF Generation Update

#### Step 4.1: Update PDF Overlay Service

**File**: `apps/pdf_forms/services/pdf_overlay.py`

**Changes**:

- Handle linked fields in PDF generation (no special logic needed)
- Linked fields are just regular fields with values

**Code**: No changes needed! The overlay service already handles all field types based on submitted form data. Linked fields are just text/choice fields with auto-populated values.

**Testing**:

- PDFs generate correctly with linked field values
- Readonly fields appear in PDF
- Values are correctly positioned

---

## Testing Strategy

### Unit Tests

**File**: `apps/pdf_forms/tests/test_data_sources.py` (NEW FILE)

```python
"""Tests for linked fields and data sources functionality."""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.pdf_forms.security import PDFFormSecurity
from apps.pdf_forms.services.data_source_utils import DataSourceUtils
from apps.pdf_forms.services.form_generator import DynamicFormGenerator


class DataSourceValidationTests(TestCase):
    """Test validation of data source configurations."""

    def test_valid_data_source(self):
        """Valid data source passes validation."""
        data_sources = {
            "procedures": [
                {"name": "Test", "code": "123"}
            ]
        }
        # Should not raise
        PDFFormSecurity.validate_data_sources(data_sources)

    def test_invalid_data_source_structure(self):
        """Invalid data source structure raises error."""
        data_sources = "not a dict"
        with self.assertRaises(ValidationError):
            PDFFormSecurity.validate_data_sources(data_sources)

    def test_empty_data_source_item(self):
        """Empty data source item raises error."""
        data_sources = {
            "procedures": [{}]
        }
        with self.assertRaises(ValidationError):
            PDFFormSecurity.validate_data_sources(data_sources)

    # ... more tests ...


class DataSourceUtilsTests(TestCase):
    """Test data source utility functions."""

    def setUp(self):
        self.form_config = {
            "data_sources": {
                "procedures": [
                    {"name": "Apendicectomia", "code": "0409010018"},
                    {"name": "Colecistectomia", "code": "0408010036"}
                ]
            },
            "fields": {
                "procedure_name": {
                    "type": "choice",
                    "data_source": "procedures",
                    "data_source_key": "name"
                },
                "procedure_code": {
                    "type": "text",
                    "data_source": "procedures",
                    "data_source_key": "code"
                }
            }
        }

    def test_get_data_source(self):
        """Can retrieve data source by name."""
        source = DataSourceUtils.get_data_source(self.form_config, "procedures")
        self.assertEqual(len(source), 2)

    def test_get_field_choices_from_source(self):
        """Can generate choices from data source."""
        field_config = self.form_config["fields"]["procedure_name"]
        choices = DataSourceUtils.get_field_choices_from_source(
            self.form_config, field_config
        )
        self.assertEqual(choices, ["Apendicectomia", "Colecistectomia"])

    # ... more tests ...


class LinkedFieldsFormGenerationTests(TestCase):
    """Test form generation with linked fields."""

    # ... tests for form generation ...
```

### Integration Tests

**File**: `apps/pdf_forms/tests/test_linked_fields_integration.py` (NEW FILE)

```python
"""Integration tests for complete linked fields workflow."""

from django.test import TestCase, Client
from django.urls import reverse
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory
from apps.patients.tests.factories import PatientFactory
from apps.accounts.tests.factories import UserFactory


class LinkedFieldsWorkflowTests(TestCase):
    """Test complete workflow from form display to PDF generation."""

    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory()
        self.client = Client()
        self.client.force_login(self.user)

        # Create template with linked fields
        self.template = PDFFormTemplateFactory(
            form_fields={
                "data_sources": {
                    "procedures": [
                        {"name": "Proc A", "code": "001"},
                        {"name": "Proc B", "code": "002"}
                    ]
                },
                "fields": {
                    "procedure_name": {
                        "type": "choice",
                        "label": "Procedure",
                        "data_source": "procedures",
                        "data_source_key": "name",
                        "x": 5, "y": 10, "width": 8, "height": 0.7
                    },
                    "procedure_code": {
                        "type": "text",
                        "label": "Code",
                        "data_source": "procedures",
                        "data_source_key": "code",
                        "linked_readonly": True,
                        "x": 14, "y": 10, "width": 4, "height": 0.7
                    }
                }
            }
        )

    def test_form_displays_with_linked_fields(self):
        """Form page loads with linked fields configuration."""
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'linked-fields-data')
        self.assertContains(response, 'pdf_forms_linked_fields.js')

    def test_form_submission_with_linked_data(self):
        """Can submit form with linked field values."""
        url = reverse('pdf_forms:form_fill', kwargs={
            'template_id': self.template.id,
            'patient_id': self.patient.id
        })
        response = self.client.post(url, {
            'procedure_name': 'Proc A',
            'procedure_code': '001'
        })

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

    # ... more integration tests ...
```

### Manual Testing Checklist

- [ ] Create new template with data sources
- [ ] Verify field configuration validates
- [ ] Fill form and verify auto-fill works
- [ ] Verify readonly fields cannot be edited
- [ ] Submit form and verify PDF generates
- [ ] Test with existing templates (backward compatibility)
- [ ] Test form without JavaScript enabled (graceful degradation)

---

## Rollout Strategy

### Phase 1: Backend Infrastructure (Days 1-2)

1. Implement backend validation and utilities (Steps 1.1 - 1.3)
2. Write unit tests for data source utilities
3. Test backward compatibility with existing configs

### Phase 2: Form Generation (Day 3)

1. Implement form generation enhancements (Step 2.1)
2. Test choice field generation from data sources
3. Verify metadata attachment to forms

### Phase 2.5: Admin UI (Days 4-5)

1. Add data source management panel (Steps 2.5.1 - 2.5.2)
2. Implement data source JavaScript (Step 2.5.3)
3. Add field linking UI (Steps 2.5.4 - 2.5.5)
4. Test complete admin workflow

### Phase 3: Frontend Enhancement (Days 6-7)

1. Implement linked fields JavaScript (Steps 3.1 - 3.2)
2. Add webpack configuration
3. Integration testing of auto-fill behavior

### Phase 4: Testing (Week 2)

1. Full integration tests (unit + integration)
2. Manual testing with real data
3. Performance testing
4. Browser compatibility testing

### Phase 5: Documentation (Week 2)

1. Update docs/apps/pdf-forms.md with new features
2. Create example configurations
3. Record admin tutorial video (optional)
4. Update help text in admin interface

### Phase 6: Deployment

1. Deploy to staging environment
2. User acceptance testing with hospital staff
3. Deploy to production
4. Monitor for issues
5. Gather user feedback

---

## Migration Path for Existing Forms

### Converting Static Choices to Data Sources

**Before** (static choices):

```json
{
  "blood_type": {
    "type": "choice",
    "label": "Tipo Sanguíneo",
    "choices": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "x": 4.5, "y": 14.0, "width": 3.0, "height": 0.7
  }
}
```

**After** (no change needed - still works!):

```json
{
  "blood_type": {
    "type": "choice",
    "label": "Tipo Sanguíneo",
    "choices": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "x": 4.5, "y": 14.0, "width": 3.0, "height": 0.7
  }
}
```

### Adding Linked Fields to Existing Form

**Step 1**: Identify fields that should be linked

```
Example: "procedure_name" and "procedure_code" both exist as separate text fields
```

**Step 2**: Create data source

```json
{
  "data_sources": {
    "procedures": [
      {"name": "Apendicectomia", "code": "0409010018"},
      {"name": "Colecistectomia", "code": "0408010036"}
    ]
  }
}
```

**Step 3**: Update field configurations

```json
{
  "procedure_name": {
    "type": "choice",  // Change from "text" to "choice"
    "data_source": "procedures",
    "data_source_key": "name",
    // ... keep existing x, y, width, height ...
  },
  "procedure_code": {
    "type": "text",
    "data_source": "procedures",
    "data_source_key": "code",
    "linked_readonly": true,
    // ... keep existing x, y, width, height ...
  }
}
```

---

## Example Configurations

### Example 1: Procedure Name and Code

```json
{
  "sections": {
    "procedure_info": {
      "label": "Informações do Procedimento",
      "order": 1,
      "collapsed": false,
      "icon": "bi-clipboard-pulse"
    }
  },
  "fields": {
    "procedure_name": {
      "type": "choice",
      "label": "Nome do Procedimento",
      "section": "procedure_info",
      "field_order": 1,
      "data_source": "procedures",
      "data_source_key": "name",
      "x": 4.5, "y": 10.0, "width": 10.0, "height": 0.7,
      "required": true
    },
    "procedure_code": {
      "type": "text",
      "label": "Código SUS",
      "section": "procedure_info",
      "field_order": 2,
      "data_source": "procedures",
      "data_source_key": "code",
      "linked_readonly": true,
      "x": 15.0, "y": 10.0, "width": 4.0, "height": 0.7,
      "required": true
    }
  },
  "data_sources": {
    "procedures": [
      {"name": "Apendicectomia", "code": "0409010018"},
      {"name": "Colecistectomia", "code": "0408010036"},
      {"name": "Hérnia inguinal", "code": "0409030059"}
    ]
  }
}
```

### Example 2: Diagnosis with ICD Code

```json
{
  "fields": {
    "diagnosis_name": {
      "type": "choice",
      "label": "Diagnóstico",
      "data_source": "diagnoses",
      "data_source_key": "name",
      "x": 4.5, "y": 12.0, "width": 10.0, "height": 0.7,
      "required": true
    },
    "icd_code": {
      "type": "text",
      "label": "CID-10",
      "data_source": "diagnoses",
      "data_source_key": "icd",
      "linked_readonly": true,
      "x": 15.0, "y": 12.0, "width": 4.0, "height": 0.7,
      "required": true
    }
  },
  "data_sources": {
    "diagnoses": [
      {"name": "Apendicite aguda", "icd": "K35"},
      {"name": "Colecistite aguda", "icd": "K81.0"},
      {"name": "Hérnia inguinal unilateral", "icd": "K40.9"}
    ]
  }
}
```

### Example 3: Three Related Fields (Procedure, Code, Category)

```json
{
  "fields": {
    "procedure_name": {
      "type": "choice",
      "label": "Procedimento",
      "data_source": "procedures",
      "data_source_key": "name",
      "x": 4.5, "y": 10.0, "width": 8.0, "height": 0.7
    },
    "procedure_code": {
      "type": "text",
      "label": "Código",
      "data_source": "procedures",
      "data_source_key": "code",
      "linked_readonly": true,
      "x": 13.0, "y": 10.0, "width": 4.0, "height": 0.7
    },
    "procedure_category": {
      "type": "text",
      "label": "Categoria",
      "data_source": "procedures",
      "data_source_key": "category",
      "linked_readonly": true,
      "x": 17.5, "y": 10.0, "width": 5.0, "height": 0.7
    }
  },
  "data_sources": {
    "procedures": [
      {
        "name": "Apendicectomia",
        "code": "0409010018",
        "category": "Cirurgia Geral"
      },
      {
        "name": "Colecistectomia",
        "code": "0408010036",
        "category": "Cirurgia Geral"
      }
    ]
  }
}
```

---

## Known Limitations and Future Enhancements

### Current Limitations

1. **Static Data Sources**: Data sources are defined in JSON config (not database-driven)
2. **No Validation**: Doesn't validate if linked field values actually match
3. **Single Data Source per Field**: Each field can only link to one data source
4. **No Conditional Logic**: Can't show/hide fields based on selection

### Future Enhancements (Not in MVP)

1. **Database-Backed Data Sources**: Store common data sources (procedures, diagnoses) in database
2. **External API Integration**: Fetch data from external APIs (e.g., SUS procedure table)
3. **Dynamic Data Sources**: Generate data sources from patient-specific data
4. **Conditional Fields**: Show/hide fields based on data source selection
5. **Admin UI**: Visual interface for managing data sources
6. **Import/Export**: Import data sources from CSV/Excel
7. **Validation Rules**: Ensure linked fields match data source structure

---

## Documentation Updates Needed

### Update docs/apps/pdf-forms.md

Add new section:

```markdown
## Linked Fields with Data Sources

**NEW: Automatically fill related fields based on dropdown selection**

### Overview

Link multiple fields through a shared data source to automatically populate related information:
- Select procedure name → auto-fill procedure code
- Select diagnosis → auto-fill ICD code
- Select medication → auto-fill dosage and route

### Configuration

[Include examples from this document]

### How It Works

1. Define a data source with all related information
2. Link fields to the data source
3. When user selects a value, related fields auto-fill
4. Readonly linked fields prevent manual editing

### Examples

[Include examples from this document]
```

---

## Questions to Clarify Before Implementation

### 1. Data Source Management

**Question**: Should we support external/database-backed data sources in MVP, or only JSON-configured sources?

**Recommendation**: Start with JSON-only for MVP. Database-backed can be Phase 2.

**Decision**: Start with JSON-only.

---

### 2. Validation Strictness

**Question**: Should we validate that linked field values match the data source structure on form submission?

**Example**: User manually edits readonly field (via browser dev tools). Should we reject the submission?

**Recommendation**: For MVP, trust the data. Add validation in Phase 2 if needed.

**Decision**: trust the data, no validation.

---

### 3. Graceful Degradation

**Question**: How should the form behave if JavaScript is disabled?

**Recommendation**:

- Show all fields (including linked ones) as editable
- User can manually fill all fields
- Form still submits and validates normally

**Decision**: follow the Recommendation (show fields as editables, user can manually fill all fields)

---

### 4. Multiple Data Sources

**Question**: Can a single field be linked to multiple data sources, or only one?

**Recommendation**: MVP supports one data source per field. Keep it simple.

**Decision**: keep one data source per field

---

### 5. Webpack Integration

**Question**: Should the new JavaScript file go through Webpack build process?

**Recommendation**: Yes, add to webpack.config.js copy patterns for consistency.

**Decision**: Yes, add to webpack.config.js

---

## Success Criteria

### Functionality

- [ ] Dropdown selection auto-fills related fields
- [ ] Readonly linked fields cannot be manually edited
- [ ] Forms without data sources work unchanged
- [ ] PDF generation includes linked field values
- [ ] Form validation works correctly

### Code Quality

- [ ] All tests pass (unit + integration)
- [ ] No breaking changes to existing templates
- [ ] Code follows project conventions
- [ ] Security validation prevents malicious configs

### Documentation

- [ ] Implementation documented in pdf-forms.md
- [ ] Example configurations provided
- [ ] Migration path documented for existing forms

### Performance

- [ ] No performance degradation for non-linked forms
- [ ] JavaScript loads only when needed
- [ ] Page load time impact < 100ms

---

## Rollback Plan

If issues are discovered in production:

1. **Immediate**: Feature is opt-in, so disable by removing data sources from templates
2. **Code**: Revert changes to `form_generator.py` and `pdf_overlay.py`
3. **JavaScript**: Remove script tag from templates
4. **Database**: No database changes, so no rollback needed

---

## Contact and Support

For questions during implementation:

- Create issue in project repository
- Tag implementation lead
- Reference this document

---

**End of Implementation Plan**
