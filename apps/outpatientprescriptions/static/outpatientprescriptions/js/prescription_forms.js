/**
 * Prescription Forms JavaScript
 * Handles dynamic form management for prescription items and drug template integration
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        formsetPrefix: 'items',
        addButtonClass: 'add-item-btn',
        removeButtonClass: 'remove-item-btn',
        formContainerClass: 'prescription-item-form',
        templateSelectClass: 'drug-template-select',
        emptyFormSelector: '#empty-form-template',
        formsetContainerSelector: '#prescription-items-container'
    };

    // DOM elements
    let formsetContainer;
    let addButton;
    let totalFormsInput;
    let emptyForm;
    let formIndex = 0;

    /**
     * Initialize the prescription form management
     */
    function initializePrescriptionForms() {
        // Find DOM elements
        formsetContainer = document.querySelector(CONFIG.formsetContainerSelector);
        if (!formsetContainer) {
            console.warn('Prescription formset container not found');
            return;
        }

        addButton = document.getElementById('add-item-btn');
        totalFormsInput = document.querySelector(`#id_${CONFIG.formsetPrefix}-TOTAL_FORMS`);
        emptyForm = document.querySelector(CONFIG.emptyFormSelector);

        if (!totalFormsInput || !emptyForm) {
            console.warn('Required formset elements not found');
            return;
        }

        // Initialize form index
        formIndex = parseInt(totalFormsInput.value) || 0;

        // Bind events
        bindEvents();
        
        // Initialize existing forms
        initializeExistingForms();
        
        // Update form order
        updateFormOrder();

        console.log('Prescription forms initialized');
    }

    /**
     * Bind event listeners
     */
    function bindEvents() {
        // Add item button
        if (addButton) {
            addButton.addEventListener('click', addPrescriptionItem);
        }

        // Remove item buttons (delegated)
        formsetContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains(CONFIG.removeButtonClass) || e.target.closest(`.${CONFIG.removeButtonClass}`)) {
                const removeBtn = e.target.classList.contains(CONFIG.removeButtonClass) ? e.target : e.target.closest(`.${CONFIG.removeButtonClass}`);
                removePrescriptionItem(removeBtn);
            }
        });

        // Drug template selection (delegated)
        formsetContainer.addEventListener('change', function(e) {
            if (e.target.classList.contains(CONFIG.templateSelectClass)) {
                handleTemplateSelection(e.target);
            }
        });

        // Form input changes to update order
        formsetContainer.addEventListener('input', updateFormOrder);
    }

    /**
     * Initialize existing forms with proper event handling
     */
    function initializeExistingForms() {
        const existingForms = formsetContainer.querySelectorAll(`.${CONFIG.formContainerClass}`);
        existingForms.forEach((form, index) => {
            setupFormEvents(form, index);
        });
    }

    /**
     * Add a new prescription item form
     */
    function addPrescriptionItem(e) {
        e.preventDefault();

        // Clone empty form template
        const emptyFormHtml = emptyForm.innerHTML;
        const newFormHtml = emptyFormHtml.replace(/__prefix__/g, formIndex);
        
        // Create new form element
        const newFormWrapper = document.createElement('div');
        newFormWrapper.innerHTML = newFormHtml;
        const newForm = newFormWrapper.firstElementChild;
        
        // Update form numbering
        const formTitle = newForm.querySelector('h6');
        if (formTitle) {
            formTitle.textContent = `Medicamento ${formIndex + 1}`;
        }

        // Append to container
        formsetContainer.appendChild(newForm);

        // Setup events for new form
        setupFormEvents(newForm, formIndex);

        // Update management form
        formIndex++;
        totalFormsInput.value = formIndex;

        // Update form order
        updateFormOrder();

        // Focus on first input of new form
        const firstInput = newForm.querySelector('input[type="text"], textarea');
        if (firstInput) {
            firstInput.focus();
        }

        console.log(`Added prescription item form ${formIndex - 1}`);
    }

    /**
     * Remove a prescription item form
     */
    function removePrescriptionItem(removeButton) {
        const form = removeButton.closest(`.${CONFIG.formContainerClass}`);
        if (!form) return;

        // Check if this is the last visible form
        const visibleForms = formsetContainer.querySelectorAll(`.${CONFIG.formContainerClass}:not([style*="display: none"])`);
        if (visibleForms.length <= 1) {
            alert('Pelo menos um item deve ser mantido na receita.');
            return;
        }

        // Mark form for deletion
        const deleteInput = form.querySelector('input[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.checked = true;
            form.style.display = 'none';
        } else {
            // Remove form entirely if it's new
            form.remove();
            formIndex--;
            totalFormsInput.value = formIndex;
        }

        // Update form order
        updateFormOrder();

        console.log('Removed prescription item form');
    }

    /**
     * Add remove button to a form
     */
    function addRemoveButton(form) {
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = `btn btn-outline-danger btn-sm ${CONFIG.removeButtonClass}`;
        removeButton.innerHTML = '<i class="fas fa-trash"></i> Remover';

        // Find a good place to insert the button
        const formActions = form.querySelector('.form-actions');
        if (formActions) {
            formActions.appendChild(removeButton);
        } else {
            // Create form actions container
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'form-actions mt-2 text-end';
            actionsDiv.appendChild(removeButton);
            form.appendChild(actionsDiv);
        }
    }

    /**
     * Setup events for a specific form
     */
    function setupFormEvents(form, index) {
        // Add remove button if it doesn't exist
        if (!form.querySelector(`.${CONFIG.removeButtonClass}`)) {
            addRemoveButton(form);
        }

        // Setup drug template selection
        const templateSelect = form.querySelector(`.${CONFIG.templateSelectClass}`);
        if (templateSelect) {
            templateSelect.addEventListener('change', () => handleTemplateSelection(templateSelect));
        }
    }

    /**
     * Handle drug template selection
     */
    function handleTemplateSelection(selectElement) {
        const selectedOption = selectElement.selectedOptions[0];
        if (!selectedOption || !selectedOption.value) return;

        const form = selectElement.closest(`.${CONFIG.formContainerClass}`);
        if (!form) return;

        // Get template data from the option
        const templateData = {
            name: selectedOption.dataset.name || selectedOption.text,
            presentation: selectedOption.dataset.presentation || '',
            usageInstructions: selectedOption.dataset.usageInstructions || ''
        };

        // Fill form fields
        fillFormFromTemplate(form, templateData);

        console.log('Applied drug template:', templateData.name);
    }

    /**
     * Fill form fields from drug template data
     */
    function fillFormFromTemplate(form, templateData) {
        const drugNameInput = form.querySelector('input[name$="-drug_name"]');
        const presentationInput = form.querySelector('input[name$="-presentation"]');
        const usageInstructionsTextarea = form.querySelector('textarea[name$="-usage_instructions"]');

        if (drugNameInput && templateData.name) {
            drugNameInput.value = templateData.name;
        }

        if (presentationInput && templateData.presentation) {
            presentationInput.value = templateData.presentation;
        }

        if (usageInstructionsTextarea && templateData.usageInstructions) {
            usageInstructionsTextarea.value = templateData.usageInstructions;
        }

        // Focus on quantity field after template is applied
        const quantityInput = form.querySelector('input[name$="-quantity"]');
        if (quantityInput) {
            quantityInput.focus();
        }
    }

    /**
     * Update form order numbers
     */
    function updateFormOrder() {
        const visibleForms = formsetContainer.querySelectorAll(`.${CONFIG.formContainerClass}:not([style*="display: none"])`);
        
        visibleForms.forEach((form, index) => {
            const orderInput = form.querySelector('input[name$="-order"]');
            if (orderInput) {
                orderInput.value = index + 1;
            }

            // Update form numbering in UI
            const formTitle = form.querySelector('.form-title, .card-header');
            if (formTitle) {
                formTitle.textContent = `Item ${index + 1}`;
            }
        });
    }

    /**
     * Load drug template data via AJAX
     */
    function loadDrugTemplateData() {
        // This function can be extended to load template data dynamically
        const templateSelects = document.querySelectorAll(`.${CONFIG.templateSelectClass}`);
        
        templateSelects.forEach(select => {
            // Enhance options with data attributes
            Array.from(select.options).forEach(option => {
                if (option.value) {
                    // Data would be loaded from the server
                    // For now, we assume data is already in the HTML
                }
            });
        });
    }

    /**
     * Validate formset before submission
     */
    function validateFormset() {
        const visibleForms = formsetContainer.querySelectorAll(`.${CONFIG.formContainerClass}:not([style*="display: none"])`);
        
        if (visibleForms.length === 0) {
            alert('Pelo menos um item deve ser adicionado à receita.');
            return false;
        }

        // Additional validation can be added here
        return true;
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializePrescriptionForms);
    } else {
        initializePrescriptionForms();
    }

    // Expose public API
    window.PrescriptionForms = {
        initialize: initializePrescriptionForms,
        addItem: addPrescriptionItem,
        validate: validateFormset
    };

})();