/**
 * Drug Template Integration JavaScript
 * Handles template selection, autocomplete, and form field population
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        templateSelectClass: 'drug-template-select',
        autocompleteClass: 'autocomplete-input',
        autocompleteContainerClass: 'autocomplete-container',
        suggestionClass: 'autocomplete-suggestions',
        loadingClass: 'loading',
        debounceDelay: 300
    };

    // Cache for template data and autocomplete results
    const cache = {
        templates: new Map(),
        autocompleteResults: new Map()
    };

    /**
     * Initialize drug template integration
     */
    function initializeDrugTemplateIntegration() {
        initializeTemplateSelects();
        initializePrescriptionTemplateSelect();
        initializeAutocomplete();
        initializeDrugNameAutocomplete();
        loadTemplateData();
    }
    

    /**
     * Initialize autocomplete for drug name fields
     */
    function initializeDrugNameAutocomplete() {
        // Add autocomplete to existing drug name fields (skip template fields with __prefix__)
        const drugNameFields = document.querySelectorAll('input[name$="-drug_name"], input[name="drug_name"]');
        
        drugNameFields.forEach((field, index) => {
            // Skip template fields with __prefix__ placeholder
            if (field.name && field.name.includes('__prefix__')) {
                return;
            }
            
            setupDrugNameAutocomplete(field);
        });
        
        // Monitor for new drug name fields (when adding prescription items)
        let isSettingUpAutocomplete = false; // Flag to prevent infinite loops
        let processedFields = new Set(); // Track processed fields to prevent duplicates
        
        const observer = new MutationObserver(mutations => {
            // Skip if we're currently setting up autocomplete (prevents infinite loops)
            if (isSettingUpAutocomplete) {
                return;
            }
            
            // Collect all new fields first
            const allNewFields = [];
            
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const newDrugNameFields = node.querySelectorAll('input[name$="-drug_name"], input[name="drug_name"]');
                        
                        // Filter out template fields and already processed fields
                        const realNewFields = Array.from(newDrugNameFields).filter(field => {
                            const fieldKey = field.name || field.id;
                            return fieldKey && 
                                   !fieldKey.includes('__prefix__') && 
                                   !processedFields.has(fieldKey);
                        });
                        
                        allNewFields.push(...realNewFields);
                    }
                });
            });
            
            // Process new fields if any
            if (allNewFields.length > 0) {
                // Set flag to prevent recursive calls
                isSettingUpAutocomplete = true;
                
                // Mark fields as processed immediately
                allNewFields.forEach(field => {
                    const fieldKey = field.name || field.id;
                    processedFields.add(fieldKey);
                });
                
                // Add delay to ensure DOM is stable and prevent infinite triggering
                setTimeout(() => {
                    try {
                        allNewFields.forEach((field, index) => {
                            // Force setup for new fields, even if they appear to have autocomplete
                            // (they might be cloned from template with broken containers)
                            setupDrugNameAutocompleteForced(field);
                        });
                    } catch (error) {
                        console.error('Error setting up autocomplete for new fields:', error);
                    } finally {
                        // Always reset flag, even if there's an error
                        setTimeout(() => {
                            isSettingUpAutocomplete = false;
                        }, 50); // Additional delay before allowing new processing
                    }
                }, 50); // Longer delay to ensure DOM stability
            }
            
            // Handle other new elements without triggering autocomplete setup
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE && !isSettingUpAutocomplete) {
                        // Initialize new template selects (search enhancement removed - using autocomplete)
                        const newTemplateSelects = node.querySelectorAll(`.${CONFIG.templateSelectClass}`);
                        newTemplateSelects.forEach(select => {
                            select.addEventListener('change', handleTemplateSelection);
                        });
                    }
                });
            });
        });
        
        const prescriptionContainer = document.getElementById('prescription-items-container');
        if (prescriptionContainer) {
            observer.observe(prescriptionContainer, { childList: true, subtree: true });
        }
    }
    
    /**
     * Setup autocomplete for a drug name field
     */
    function setupDrugNameAutocomplete(field) {
        if (field.hasAttribute('data-autocomplete-enabled')) {
            return; // Already enabled
        }
        
        _setupDrugNameAutocompleteInternal(field);
    }

    /**
     * Force setup autocomplete for a drug name field (ignores existing setup)
     */
    function setupDrugNameAutocompleteForced(field) {
        // Check if field is still valid and attached to DOM
        if (!field || !field.parentNode || !document.contains(field)) {
            return;
        }
        
        // Remove any existing autocomplete setup first
        if (field.hasAttribute('data-autocomplete-enabled')) {
            field.removeAttribute('data-autocomplete-enabled');
            field.classList.remove(CONFIG.autocompleteClass);
            
            // Remove existing autocomplete container if it exists
            const existingContainer = field.closest(`.${CONFIG.autocompleteContainerClass}`);
            if (existingContainer && existingContainer.parentNode && existingContainer !== field.parentNode) {
                try {
                    // Move field out of container before removing container
                    existingContainer.parentNode.insertBefore(field, existingContainer);
                    existingContainer.remove();
                } catch (error) {
                    console.error('Error removing existing autocomplete container:', error);
                }
            }
        }
        
        // Double-check field is still valid after cleanup
        if (!field.parentNode || !document.contains(field)) {
            return;
        }
        
        _setupDrugNameAutocompleteInternal(field);
    }

    /**
     * Internal function to setup autocomplete (used by both regular and forced setup)
     */
    function _setupDrugNameAutocompleteInternal(field) {
        try {
            // Final validation
            if (!field || !field.parentNode || !document.contains(field)) {
                return;
            }
            
            // Check if already in an autocomplete container
            const existingContainer = field.closest(`.${CONFIG.autocompleteContainerClass}`);
            if (existingContainer) {
                field.setAttribute('data-autocomplete-enabled', 'true');
                field.classList.add(CONFIG.autocompleteClass);
                setupAutocomplete(field);
                return;
            }
            
            field.setAttribute('data-autocomplete-enabled', 'true');
            field.classList.add(CONFIG.autocompleteClass);
            
            // Create autocomplete container
            const container = document.createElement('div');
            container.className = CONFIG.autocompleteContainerClass + ' position-relative';
            
            // Create suggestions container
            const suggestionsContainer = document.createElement('div');
            suggestionsContainer.className = CONFIG.suggestionClass + ' position-absolute w-100 border border-top-0 rounded-bottom shadow-sm';
            suggestionsContainer.style.display = 'none';
            suggestionsContainer.style.zIndex = '1000';
            suggestionsContainer.style.maxHeight = '200px';
            suggestionsContainer.style.overflowY = 'auto';
            
            // Store parent and next sibling for safe insertion
            const parent = field.parentNode;
            const nextSibling = field.nextSibling;
            
            // Wrap field in container
            parent.insertBefore(container, nextSibling);
            container.appendChild(field);
            container.appendChild(suggestionsContainer);
            
            // Setup autocomplete behavior
            setupAutocomplete(field);
            
        } catch (error) {
            console.error('Error in internal autocomplete setup:', error);
            // Try to cleanup on error
            if (field && field.hasAttribute) {
                field.removeAttribute('data-autocomplete-enabled');
                field.classList.remove(CONFIG.autocompleteClass);
            }
        }
    }


    // Manual entry toggles removed - autocomplete is now always available on drug name fields

    /**
     * Initialize template select dropdowns
     */
    function initializeTemplateSelects() {
        const templateSelects = document.querySelectorAll(`.${CONFIG.templateSelectClass}`);
        
        templateSelects.forEach(select => {
            select.addEventListener('change', handleTemplateSelection);
        });
    }

    /**
     * Initialize prescription template select dropdown
     */
    function initializePrescriptionTemplateSelect() {
        const prescriptionTemplateSelect = document.getElementById('prescription-template-select');
        
        if (prescriptionTemplateSelect) {
            prescriptionTemplateSelect.addEventListener('change', handlePrescriptionTemplateSelection);
        }
    }


    // Manual entry toggle function removed - no longer needed

    /**
     * Handle template selection and populate form fields
     */
    function handleTemplateSelection(event) {
        const select = event.target;
        const selectedOption = select.selectedOptions[0];
        
        if (!selectedOption || !selectedOption.value) {
            return;
        }

        const templateData = extractTemplateData(selectedOption);
        if (templateData) {
            populateFormFields(select, templateData);
            showTemplateAppliedNotification(templateData.name);
        }
    }

    /**
     * Handle prescription template selection and populate all medication forms
     */
    function handlePrescriptionTemplateSelection(event) {
        const select = event.target;
        const templateId = select.value;
        
        if (!templateId) {
            return;
        }

        // Show loading state
        select.disabled = true;
        const originalText = select.options[select.selectedIndex].textContent;
        select.options[select.selectedIndex].textContent = 'Carregando...';

        // Fetch template data
        fetchPrescriptionTemplateData(templateId)
            .then(templateData => {
                applyPrescriptionTemplate(templateData);
                showTemplateAppliedNotification(`Template "${templateData.name}" aplicado com ${templateData.items.length} medicamentos`);
                
                // Reset select to empty option
                select.selectedIndex = 0;
            })
            .catch(error => {
                console.error('Error applying prescription template:', error);
                showErrorNotification('Erro ao aplicar template de prescrição');
            })
            .finally(() => {
                // Restore original state
                select.disabled = false;
                select.options[select.selectedIndex].textContent = originalText;
            });
    }


    /**
     * Extract template data from select option
     */
    function extractTemplateData(option) {
        return {
            id: option.dataset.templateId || option.value,
            name: option.dataset.name || option.textContent,
            presentation: option.dataset.presentation || '',
            usageInstructions: option.dataset.usageInstructions || option.dataset.instructions || ''
        };
    }

    /**
     * Populate form fields with template data
     */
    function populateFormFields(selectElement, templateData) {
        const form = selectElement.closest('.prescription-item-form, form');
        if (!form) return;

        // Find and populate form fields
        const fields = {
            drugName: form.querySelector('input[name$="-drug_name"], input[name="drug_name"]'),
            presentation: form.querySelector('input[name$="-presentation"], input[name="presentation"]'),
            quantity: form.querySelector('input[name$="-quantity"], input[name="quantity"]'),
            usageInstructions: form.querySelector('textarea[name$="-usage_instructions"], textarea[name="usage_instructions"]'),
            sourceTemplate: form.querySelector('input[name$="-source_template"], input[name="source_template"]')
        };

        // Populate fields with animation
        Object.entries(fields).forEach(([fieldName, element]) => {
            if (element && templateData[getDataKey(fieldName)]) {
                const value = templateData[getDataKey(fieldName)];
                
                // Special handling for sourceTemplate field (no animation)
                if (fieldName === 'sourceTemplate') {
                    element.value = value;
                } else if (value && value.trim()) {
                    // Always populate field with template value
                    animateFieldUpdate(element, value);
                }
            }
        });

        // Focus on quantity field after population
        const quantityField = form.querySelector('input[name$="-quantity"], input[name="quantity"]');
        if (quantityField) {
            setTimeout(() => quantityField.focus(), 300);
        }
    }
    

    /**
     * Get data key for field name
     */
    function getDataKey(fieldName) {
        const mapping = {
            drugName: 'name',
            presentation: 'presentation',
            quantity: 'quantity',
            usageInstructions: 'usageInstructions',
            sourceTemplate: 'id'
        };
        return mapping[fieldName] || fieldName;
    }

    /**
     * Animate field update
     */
    function animateFieldUpdate(element, value) {
        if (!element) return;
        
        // Add animation class
        element.classList.add('field-updating');
        
        // Set value with delay for visual effect
        setTimeout(() => {
            element.value = value;
            element.classList.remove('field-updating');
            element.classList.add('field-updated');
            
            // Remove updated class after animation
            setTimeout(() => {
                element.classList.remove('field-updated');
            }, 1000);
        }, 100);
    }

    /**
     * Initialize autocomplete functionality
     */
    function initializeAutocomplete() {
        const autocompleteInputs = document.querySelectorAll(`.${CONFIG.autocompleteClass}`);
        
        autocompleteInputs.forEach(input => {
            setupAutocomplete(input);
        });
    }

    /**
     * Setup autocomplete for an input element
     */
    function setupAutocomplete(input) {
        const container = input.closest(`.${CONFIG.autocompleteContainerClass}`);
        if (!container) {
            console.error('No autocomplete container found for input:', input.name || input.id);
            return;
        }

        const suggestionsContainer = container.querySelector(`.${CONFIG.suggestionClass}`);
        if (!suggestionsContainer) {
            console.error('No suggestions container found for input:', input.name || input.id);
            return;
        }

        let debounceTimer;

        // Input event for autocomplete
        input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                handleAutocompleteInput(input, suggestionsContainer);
            }, CONFIG.debounceDelay);
        });

        // Focus and blur events
        input.addEventListener('focus', () => {
            if (input.value.length > 0) {
                showSuggestions(suggestionsContainer);
            }
        });

        input.addEventListener('blur', (e) => {
            // Delay hiding to allow for suggestion clicks
            setTimeout(() => {
                hideSuggestions(suggestionsContainer);
            }, 200);
        });

        // Keyboard navigation
        input.addEventListener('keydown', (e) => {
            handleAutocompleteKeyboard(e, suggestionsContainer);
        });
    }

    /**
     * Handle autocomplete input
     */
    function handleAutocompleteInput(input, suggestionsContainer) {
        const query = input.value.trim();
        
        if (query.length < 2) {
            hideSuggestions(suggestionsContainer);
            clearErrorState(input);
            return;
        }

        // Check cache first
        if (cache.autocompleteResults.has(query)) {
            displaySuggestions(suggestionsContainer, cache.autocompleteResults.get(query), input);
            clearErrorState(input);
            return;
        }

        // Show loading state
        showLoadingState(input);
        clearErrorState(input);

        // Fetch suggestions with timeout
        const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Request timeout')), 10000)
        );

        Promise.race([fetchAutocompleteSuggestions(query), timeoutPromise])
            .then(suggestions => {
                if (Array.isArray(suggestions)) {
                    cache.autocompleteResults.set(query, suggestions);
                    displaySuggestions(suggestionsContainer, suggestions, input);
                    clearErrorState(input);
                } else {
                    throw new Error('Invalid response format');
                }
            })
            .catch(error => {
                console.error('Autocomplete error:', error);
                showErrorState(input, error.message);
                displayErrorSuggestions(suggestionsContainer, error);
            })
            .finally(() => {
                hideLoadingState(input);
            });
    }

    /**
     * Fetch autocomplete suggestions
     */
    async function fetchAutocompleteSuggestions(query) {
        try {
            const url = `/prescriptions/ajax/drug-templates/search/?q=${encodeURIComponent(query)}&limit=10`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            return data.results.map(template => ({
                id: template.id,
                name: template.name,
                presentation: template.presentation,
                usage_instructions: template.usage_instructions,
                display_text: template.display_text,
                creator: template.creator,
                is_public: template.is_public,
                type: template.type // Only 'drug_template' now
            }));
            
        } catch (error) {
            console.error('Error fetching drug template suggestions:', error);
            
            // Determine error type for better handling
            let errorType = 'unknown';
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorType = 'network';
            } else if (error.message.includes('timeout')) {
                errorType = 'timeout';
            } else if (error.message.includes('403')) {
                errorType = 'permission';
            }
            
            // Fallback to cached data with error info
            const suggestions = [];
            cache.templates.forEach(template => {
                if (template.name.toLowerCase().includes(query.toLowerCase()) ||
                    template.presentation.toLowerCase().includes(query.toLowerCase())) {
                    suggestions.push({
                        id: template.id,
                        name: template.name,
                        presentation: template.presentation,
                        usage_instructions: template.usageInstructions,
                        display_text: `${template.name} - ${template.presentation}`,
                        type: 'template',
                        fallback: true
                    });
                }
            });
            
            // If no cached results and network error, throw for proper error handling
            if (suggestions.length === 0 && errorType === 'network') {
                const networkError = new Error('network');
                networkError.originalError = error;
                throw networkError;
            }
            
            return suggestions;
        }
    }

    /**
     * Display autocomplete suggestions
     */
    function displaySuggestions(container, suggestions, input) {
        container.innerHTML = '';
        
        if (suggestions.length === 0) {
            container.innerHTML = '<div class="no-suggestions">Nenhum resultado encontrado</div>';
            showSuggestions(container);
            return;
        }

        suggestions.forEach(suggestion => {
            const suggestionElement = createSuggestionElement(suggestion, input);
            container.appendChild(suggestionElement);
        });

        showSuggestions(container);
    }

    /**
     * Create suggestion element
     */
    function createSuggestionElement(suggestion, input) {
        const element = document.createElement('div');
        element.className = 'autocomplete-suggestion d-flex justify-content-between align-items-center p-2 border-bottom';
        element.style.cursor = 'pointer';
        
        const leftContent = document.createElement('div');
        
        // Build the content based on suggestion type
        let nameDisplay = suggestion.name;
        let presentationDisplay = suggestion.presentation;
        let typeIndicator = '';
        
        typeIndicator = '<small class="text-success"><i class="bi bi-capsule"></i> Template Individual</small><br>';
        
        leftContent.innerHTML = `
            ${typeIndicator}
            <div class="suggestion-name fw-bold">${nameDisplay}</div>
            <div class="suggestion-presentation text-muted small">${presentationDisplay}</div>
        `;
        
        const rightContent = document.createElement('div');
        rightContent.className = 'text-end';
        if (suggestion.creator) {
            rightContent.innerHTML = `
                <small class="text-muted">
                    ${suggestion.is_public ? '<i class="bi bi-globe"></i>' : '<i class="bi bi-person"></i>'} 
                    ${suggestion.creator}
                </small>
            `;
        }
        
        element.appendChild(leftContent);
        element.appendChild(rightContent);

        // Hover effects
        element.addEventListener('mouseenter', () => {
            element.classList.add('bg-light');
        });
        
        element.addEventListener('mouseleave', () => {
            element.classList.remove('bg-light');
        });

        element.addEventListener('click', () => {
            selectSuggestion(suggestion, input);
        });

        return element;
    }

    /**
     * Select autocomplete suggestion
     */
    function selectSuggestion(suggestion, input) {
        try {
            input.value = suggestion.name;
            
            // If this is a template suggestion, populate related fields
            if (suggestion.type === 'drug_template') {
                // Validate and sanitize template data
                const templateData = validateTemplateData({
                    id: suggestion.id,
                    name: suggestion.name,
                    presentation: suggestion.presentation,
                    usageInstructions: suggestion.usage_instructions
                });
                
                // Cache the template data
                cache.templates.set(suggestion.id, templateData);
                
                // Populate form fields
                populateFormFields(input, templateData);
                
                // Show success notification
                showTemplateAppliedNotification(`Template individual aplicado: ${suggestion.name}`);
            }

            const suggestionContainer = input.closest(`.${CONFIG.autocompleteContainerClass}`)?.querySelector(`.${CONFIG.suggestionClass}`);
            if (suggestionContainer) {
                hideSuggestions(suggestionContainer);
            }
            
            // Clear any error states
            clearErrorState(input);
            
            // Trigger change event
            input.dispatchEvent(new Event('change'));
            
        } catch (error) {
            console.error('Error selecting suggestion:', error);
            showErrorState(input, 'Erro ao aplicar template');
            
            // Show error notification
            const errorNotification = document.createElement('div');
            errorNotification.className = 'alert alert-danger alert-dismissible fade show';
            errorNotification.innerHTML = `
                <i class="bi bi-exclamation-triangle"></i>
                Erro ao aplicar template: ${error.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            const container = input.closest('.prescription-item-form, form');
            if (container) {
                container.insertBefore(errorNotification, container.firstChild);
                
                setTimeout(() => {
                    if (errorNotification.parentElement) {
                        errorNotification.remove();
                    }
                }, 5000);
            }
        }
    }

    /**
     * Show suggestions container
     */
    function showSuggestions(container) {
        container.style.display = 'block';
    }

    /**
     * Hide suggestions container
     */
    function hideSuggestions(container) {
        container.style.display = 'none';
    }

    /**
     * Show loading state
     */
    function showLoadingState(input) {
        input.classList.add(CONFIG.loadingClass);
    }

    /**
     * Hide loading state
     */
    function hideLoadingState(input) {
        input.classList.remove(CONFIG.loadingClass);
    }

    /**
     * Handle keyboard navigation in autocomplete
     */
    function handleAutocompleteKeyboard(event, suggestionsContainer) {
        const suggestions = suggestionsContainer.querySelectorAll('.autocomplete-suggestion');
        const activeSuggestion = suggestionsContainer.querySelector('.autocomplete-suggestion.active');
        
        let activeIndex = activeSuggestion ? Array.from(suggestions).indexOf(activeSuggestion) : -1;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
                setActiveSuggestion(suggestions, activeIndex);
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                activeIndex = Math.max(activeIndex - 1, -1);
                setActiveSuggestion(suggestions, activeIndex);
                break;
                
            case 'Enter':
                if (activeSuggestion) {
                    event.preventDefault();
                    activeSuggestion.click();
                }
                break;
                
            case 'Escape':
                hideSuggestions(suggestionsContainer);
                break;
        }
    }

    /**
     * Set active suggestion for keyboard navigation
     */
    function setActiveSuggestion(suggestions, activeIndex) {
        suggestions.forEach((suggestion, index) => {
            suggestion.classList.toggle('active', index === activeIndex);
        });
    }

    /**
     * Load template data for caching
     */
    function loadTemplateData() {
        // This would typically fetch from an API endpoint
        // For now, we'll extract from existing select elements
        const templateSelects = document.querySelectorAll(`.${CONFIG.templateSelectClass}`);
        
        templateSelects.forEach(select => {
            Array.from(select.options).forEach(option => {
                if (option.value && option.value !== '') {
                    const templateData = extractTemplateData(option);
                    cache.templates.set(templateData.id, templateData);
                }
            });
        });
    }

    /**
     * Enhance select with search functionality (REMOVED - causing duplicate inputs)
     * Now using unified autocomplete approach instead of separate dropdown search
     */

    /**
     * Filter select options based on search query
     */
    function filterSelectOptions(select, query) {
        const lowerQuery = query.toLowerCase();
        
        Array.from(select.options).forEach(option => {
            if (option.value === '') {
                option.style.display = '';
                return;
            }
            
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(lowerQuery) ? '' : 'none';
        });
    }

    /**
     * Fetch prescription template data from server
     */
    async function fetchPrescriptionTemplateData(templateId) {
        try {
            const url = `/prescriptions/ajax/prescription-template/${templateId}/`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            return data;
        } catch (error) {
            console.error('Error fetching prescription template data:', error);
            throw error;
        }
    }

    /**
     * Apply prescription template to form (populate all medication items)
     */
    function applyPrescriptionTemplate(templateData) {
        try {
            console.log('Applying prescription template:', templateData);
            
            const container = document.getElementById('prescription-items-container');
            if (!container) {
                throw new Error('Prescription items container not found');
            }

            // Add new items for each template item (no clearing, just add)
            console.log('Adding', templateData.items.length, 'items from template');
            templateData.items.forEach((item, index) => {
                console.log(`Adding item ${index + 1}:`, item);
                const newForm = addNewPrescriptionItem();
                if (newForm) {
                    console.log('New form created:', newForm);
                    console.log('Initial form display style:', newForm.style.display);
                    console.log('Form classes:', newForm.className);
                    
                    // Force form to be visible - remove any display: none
                    newForm.style.display = '';
                    console.log('After forcing visible, display style:', newForm.style.display);
                    
                    // Add a small delay to ensure the form is fully rendered, then populate
                    setTimeout(() => {
                        // Double-check visibility after timeout
                        console.log('Before populating, display style:', newForm.style.display);
                        if (newForm.style.display === 'none') {
                            console.warn('Form was hidden again! Forcing visible again');
                            newForm.style.display = '';
                        }
                        
                        populatePrescriptionItemForm(newForm, item);
                        
                        // Final check after population
                        console.log('After populating, display style:', newForm.style.display);
                    }, 100 * (index + 1)); // Stagger the delays more
                } else {
                    console.error('Failed to create new form for item', index);
                }
            });

            // Update form management data and remove empty forms (with delay to ensure all forms are populated)
            setTimeout(() => {
                removeEmptyDrugFormsAfterTemplate();
                updateFormsetManagement();
            }, 1000);

        } catch (error) {
            console.error('Error applying prescription template:', error);
            throw error;
        }
    }

    /**
     * Remove empty drug forms after template application (forms with empty drug_name field)
     */
    function removeEmptyDrugFormsAfterTemplate() {
        console.log('Removing empty drug forms after template application...');
        
        const allForms = document.querySelectorAll('.prescription-item-form');
        let removedCount = 0;
        
        allForms.forEach(form => {
            // Skip the template form (used for creating new forms)
            const formIndex = form.getAttribute('data-form-index');
            if (formIndex === '__prefix__') {
                console.log('Skipping template form with __prefix__');
                return;
            }
            
            // Skip already hidden forms
            if (form.style.display === 'none') {
                return;
            }
            
            const drugNameField = form.querySelector('input[name$="-drug_name"], input[name="drug_name"]');
            
            if (drugNameField && (!drugNameField.value || drugNameField.value.trim() === '')) {
                console.log('Found empty drug form after template, removing:', form);
                
                const deleteCheckbox = form.querySelector('input[name$="-DELETE"]');
                if (deleteCheckbox) {
                    // This is an existing form with a DELETE checkbox - mark for deletion
                    deleteCheckbox.checked = true;
                    form.style.display = 'none';
                } else {
                    // This is a new form without DELETE checkbox - remove entirely
                    form.remove();
                }
                removedCount++;
            }
        });
        
        console.log(`Removed ${removedCount} empty drug forms after template`);
        
        // Update form numbering after removal
        if (removedCount > 0) {
            updateFormNumbering();
        }
    }

    /**
     * Remove empty drug forms (forms with empty drug_name field) - for manual use
     */
    function removeEmptyDrugForms() {
        console.log('Manually removing empty drug forms...');
        
        const allForms = document.querySelectorAll('.prescription-item-form:not([style*="display: none"])');
        let removedCount = 0;
        
        allForms.forEach(form => {
            const drugNameField = form.querySelector('input[name$="-drug_name"], input[name="drug_name"]');
            
            if (drugNameField && (!drugNameField.value || drugNameField.value.trim() === '')) {
                console.log('Found empty drug form, removing:', form);
                
                const deleteCheckbox = form.querySelector('input[name$="-DELETE"]');
                if (deleteCheckbox) {
                    // This is an existing form with a DELETE checkbox - mark for deletion
                    deleteCheckbox.checked = true;
                    form.style.display = 'none';
                } else {
                    // This is a new form without DELETE checkbox - remove entirely
                    form.remove();
                }
                removedCount++;
            }
        });
        
        console.log(`Manually removed ${removedCount} empty drug forms`);
        
        // Update form numbering after removal
        if (removedCount > 0) {
            updateFormNumbering();
        }
    }

    /**
     * Update form numbering for all visible forms
     */
    function updateFormNumbering() {
        const container = document.getElementById('prescription-items-container');
        if (!container) return;
        
        const visibleForms = container.querySelectorAll('.prescription-item-form:not([style*="display: none"])');
        
        visibleForms.forEach((form, index) => {
            // Update form title
            const formTitle = form.querySelector('h6');
            if (formTitle) {
                formTitle.innerHTML = `<i class="bi bi-pill me-1"></i>Medicamento ${index + 1}`;
            }
            
            // Update order field
            const orderInput = form.querySelector('input[name$="-order"]');
            if (orderInput) {
                orderInput.value = index + 1;
            }
        });
        
        console.log(`Updated numbering for ${visibleForms.length} forms`);
    }

    /**
     * Clear all existing prescription items
     */
    function clearAllPrescriptionItems() {
        const existingItems = document.querySelectorAll('.prescription-item-form');
        existingItems.forEach(item => {
            const deleteCheckbox = item.querySelector('input[name$="-DELETE"]');
            if (deleteCheckbox) {
                // This is an existing form with a DELETE checkbox - mark for deletion
                deleteCheckbox.checked = true;
                item.style.display = 'none';
            } else {
                // This is a new form without DELETE checkbox - remove entirely
                item.remove();
            }
        });
    }

    /**
     * Add new prescription item form
     */
    function addNewPrescriptionItem() {
        console.log('addNewPrescriptionItem called');
        console.log('window.PrescriptionForms:', window.PrescriptionForms);
        
        // Use existing add item functionality if available
        if (window.PrescriptionForms && typeof window.PrescriptionForms.addItem === 'function') {
            console.log('Using PrescriptionForms.addItem');
            // Create a synthetic event
            const syntheticEvent = { preventDefault: () => {} };
            const newForm = window.PrescriptionForms.addItem(syntheticEvent);
            console.log('PrescriptionForms.addItem returned:', newForm);
            return newForm;
        } else {
            console.log('Fallback: using add button click');
            // Fallback: trigger the add item button
            const addButton = document.getElementById('add-item-btn');
            if (addButton) {
                console.log('Clicking add button');
                addButton.click();
                // Return the newly added form (assume it's the last one)
                const forms = document.querySelectorAll('.prescription-item-form:not([style*="display: none"])');
                console.log('Found', forms.length, 'forms after button click');
                return forms[forms.length - 1];
            } else {
                console.error('Add button not found');
            }
        }
        return null;
    }

    /**
     * Populate a single prescription item form with template data
     */
    function populatePrescriptionItemForm(form, itemData) {
        const fields = {
            drugName: form.querySelector('input[name$="-drug_name"], input[name="drug_name"]'),
            presentation: form.querySelector('input[name$="-presentation"], input[name="presentation"]'),
            quantity: form.querySelector('input[name$="-quantity"], input[name="quantity"]'),
            usageInstructions: form.querySelector('textarea[name$="-usage_instructions"], textarea[name="usage_instructions"]'),
            order: form.querySelector('input[name$="-order"], input[name="order"]')
        };

        // Populate fields with data
        if (fields.drugName) fields.drugName.value = itemData.drug_name || '';
        if (fields.presentation) fields.presentation.value = itemData.presentation || '';
        if (fields.quantity) fields.quantity.value = itemData.quantity || '';
        if (fields.usageInstructions) fields.usageInstructions.value = itemData.usage_instructions || '';
        if (fields.order) fields.order.value = itemData.order || 0;
    }

    /**
     * Update formset management form data
     */
    function updateFormsetManagement() {
        const managementForm = document.querySelector('input[name="items-TOTAL_FORMS"]');
        if (managementForm) {
            const visibleForms = document.querySelectorAll('.prescription-item-form:not([style*="display: none"])').length;
            managementForm.value = visibleForms;
            console.log('Updated TOTAL_FORMS to:', visibleForms);
        } else {
            console.warn('TOTAL_FORMS input not found');
        }
    }

    /**
     * Show template applied notification
     */
    function showTemplateAppliedNotification(templateName) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'alert alert-success template-notification';
        notification.innerHTML = `
            <i class="bi bi-check-circle"></i>
            Template "${templateName}" aplicado com sucesso!
        `;
        
        // Insert notification
        const form = document.querySelector('.prescription-item-form, form');
        if (form) {
            form.insertBefore(notification, form.firstChild);
            
            // Remove notification after delay
            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }

    /**
     * Show error notification
     */
    function showErrorNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'alert alert-danger template-notification';
        notification.innerHTML = `
            <i class="bi bi-exclamation-triangle"></i>
            ${message}
        `;
        
        // Insert notification
        const form = document.querySelector('.prescription-item-form, form');
        if (form) {
            form.insertBefore(notification, form.firstChild);
            
            // Remove notification after delay
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    }

    /**
     * Show error state on input field
     */
    function showErrorState(input, errorMessage) {
        input.classList.add('is-invalid');
        input.setAttribute('data-error', errorMessage);
        
        // Add tooltip or error message display
        input.title = `Erro: ${errorMessage}`;
    }

    /**
     * Clear error state from input field
     */
    function clearErrorState(input) {
        input.classList.remove('is-invalid');
        input.removeAttribute('data-error');
        input.removeAttribute('title');
    }

    /**
     * Display error suggestions in autocomplete
     */
    function displayErrorSuggestions(container, error) {
        container.innerHTML = '';
        
        const errorElement = document.createElement('div');
        errorElement.className = 'no-suggestions text-danger';
        
        let errorMessage = 'Erro ao buscar sugestões';
        if (error.message.includes('timeout')) {
            errorMessage = 'Tempo limite excedido. Tente novamente.';
        } else if (error.message.includes('network')) {
            errorMessage = 'Erro de conexão. Verifique sua internet.';
        } else if (error.message.includes('403')) {
            errorMessage = 'Acesso negado. Verifique suas permissões.';
        }
        
        errorElement.innerHTML = `
            <i class="bi bi-exclamation-triangle"></i>
            ${errorMessage}
            <br>
            <small class="text-muted">Clique para tentar novamente</small>
        `;
        
        errorElement.style.cursor = 'pointer';
        errorElement.addEventListener('click', () => {
            const input = container.parentElement.querySelector('input');
            if (input) {
                // Clear cache and retry
                cache.autocompleteResults.clear();
                input.dispatchEvent(new Event('input'));
            }
        });
        
        container.appendChild(errorElement);
        showSuggestions(container);
    }

    /**
     * Handle network errors gracefully
     */
    function handleNetworkError(error, input) {
        console.error('Network error in drug template integration:', error);
        
        // Show user-friendly error message
        const errorNotification = document.createElement('div');
        errorNotification.className = 'alert alert-warning alert-dismissible fade show';
        errorNotification.innerHTML = `
            <i class="bi bi-exclamation-triangle"></i>
            Erro ao carregar templates. Usando dados locais disponíveis.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = input.closest('.prescription-item-form, form');
        if (container) {
            container.insertBefore(errorNotification, container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (errorNotification.parentElement) {
                    errorNotification.remove();
                }
            }, 5000);
        }
    }

    /**
     * Validate template data before population
     */
    function validateTemplateData(templateData) {
        const requiredFields = ['id', 'name'];
        const missingFields = requiredFields.filter(field => !templateData[field]);
        
        if (missingFields.length > 0) {
            throw new Error(`Template data missing required fields: ${missingFields.join(', ')}`);
        }
        
        // Sanitize data
        return {
            id: String(templateData.id),
            name: String(templateData.name || ''),
            presentation: String(templateData.presentation || ''),
            usageInstructions: String(templateData.usageInstructions || templateData.usage_instructions || '')
        };
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeDrugTemplateIntegration);
    } else {
        initializeDrugTemplateIntegration();
    }

    // Expose public API
    window.DrugTemplateIntegration = {
        initialize: initializeDrugTemplateIntegration,
        populateFromTemplate: populateFormFields,
        removeEmptyForms: removeEmptyDrugForms,
        cache: cache
    };

})();