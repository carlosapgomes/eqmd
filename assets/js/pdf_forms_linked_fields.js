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