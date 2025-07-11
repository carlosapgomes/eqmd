/**
 * Drug Template Integration JavaScript
 * Handles template selection, autocomplete, and form field population
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        templateSelectClass: 'drug-template-select',
        prescriptionTemplateItemSelectClass: 'prescription-template-item-select',
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
        initializePrescriptionTemplateItemSelects();
        initializeManualEntryToggles();
        initializeAutocomplete();
        initializeDrugNameAutocomplete();
        loadTemplateData();
        
        console.log('Drug template integration initialized');
    }
    

    /**
     * Initialize autocomplete for drug name fields
     */
    function initializeDrugNameAutocomplete() {
        // Add autocomplete to existing drug name fields
        const drugNameFields = document.querySelectorAll('input[name$="-drug_name"], input[name="drug_name"]');
        
        drugNameFields.forEach(field => {
            setupDrugNameAutocomplete(field);
        });
        
        // Monitor for new drug name fields (when adding prescription items)
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const newDrugNameFields = node.querySelectorAll('input[name$="-drug_name"], input[name="drug_name"]');
                        newDrugNameFields.forEach(field => {
                            setupDrugNameAutocomplete(field);
                        });
                        
                        // Initialize new template selects
                        const newTemplateSelects = node.querySelectorAll(`.${CONFIG.templateSelectClass}`);
                        newTemplateSelects.forEach(select => {
                            select.addEventListener('change', handleTemplateSelection);
                            enhanceSelectWithSearch(select);
                        });
                        
                        // Initialize new prescription template item selects
                        const newPrescriptionTemplateSelects = node.querySelectorAll(`.${CONFIG.prescriptionTemplateItemSelectClass}`);
                        newPrescriptionTemplateSelects.forEach(select => {
                            select.addEventListener('change', handlePrescriptionTemplateItemSelection);
                            enhanceSelectWithSearch(select);
                        });
                        
                        // Initialize new manual entry toggles
                        const newManualEntryCheckboxes = node.querySelectorAll('input[type="checkbox"][id^="manual-entry-"]');
                        newManualEntryCheckboxes.forEach(checkbox => {
                            checkbox.addEventListener('change', handleManualEntryToggle);
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
        
        field.setAttribute('data-autocomplete-enabled', 'true');
        field.classList.add(CONFIG.autocompleteClass);
        
        // Create autocomplete container
        const container = document.createElement('div');
        container.className = CONFIG.autocompleteContainerClass + ' position-relative';
        
        // Create suggestions container
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = CONFIG.suggestionClass + ' position-absolute w-100 bg-white border border-top-0 rounded-bottom shadow-sm';
        suggestionsContainer.style.display = 'none';
        suggestionsContainer.style.zIndex = '1000';
        suggestionsContainer.style.maxHeight = '200px';
        suggestionsContainer.style.overflowY = 'auto';
        
        // Wrap field in container
        field.parentNode.insertBefore(container, field);
        container.appendChild(field);
        container.appendChild(suggestionsContainer);
        
        // Setup autocomplete behavior
        setupAutocomplete(field);
    }

    /**
     * Initialize prescription template item select dropdowns
     */
    function initializePrescriptionTemplateItemSelects() {
        const templateItemSelects = document.querySelectorAll(`.${CONFIG.prescriptionTemplateItemSelectClass}`);
        
        templateItemSelects.forEach(select => {
            select.addEventListener('change', handlePrescriptionTemplateItemSelection);
            
            // Enhance with search functionality if needed
            enhanceSelectWithSearch(select);
        });
    }

    /**
     * Initialize manual entry toggles
     */
    function initializeManualEntryToggles() {
        const manualEntryCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="manual-entry-"]');
        
        manualEntryCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', handleManualEntryToggle);
        });
    }

    /**
     * Initialize template select dropdowns
     */
    function initializeTemplateSelects() {
        const templateSelects = document.querySelectorAll(`.${CONFIG.templateSelectClass}`);
        
        templateSelects.forEach(select => {
            select.addEventListener('change', handleTemplateSelection);
            
            // Enhance with search functionality if needed
            enhanceSelectWithSearch(select);
        });
    }

    /**
     * Handle prescription template item selection and populate form fields
     */
    function handlePrescriptionTemplateItemSelection(event) {
        const select = event.target;
        const selectedOption = select.selectedOptions[0];
        
        if (!selectedOption || !selectedOption.value) {
            return;
        }

        const templateData = extractPrescriptionTemplateItemData(selectedOption);
        if (templateData) {
            populateFormFields(select, templateData);
            showTemplateAppliedNotification(`${templateData.templateName}: ${templateData.drugName}`);
            
            // Clear manual entry checkbox and hide manual section
            const formIndex = select.dataset.formIndex;
            const manualCheckbox = document.getElementById(`manual-entry-${formIndex}`);
            const manualSection = document.querySelector(`.manual-entry-section[data-form-index="${formIndex}"]`);
            
            if (manualCheckbox) {
                manualCheckbox.checked = false;
            }
            if (manualSection) {
                manualSection.style.display = 'none';
            }
        }
    }

    /**
     * Handle manual entry toggle
     */
    function handleManualEntryToggle(event) {
        const checkbox = event.target;
        const formIndex = checkbox.dataset.formIndex;
        const manualSection = document.querySelector(`.manual-entry-section[data-form-index="${formIndex}"]`);
        const prescriptionTemplateSelect = document.querySelector(`.prescription-template-item-select[data-form-index="${formIndex}"]`);
        
        if (manualSection) {
            if (checkbox.checked) {
                manualSection.style.display = 'block';
                // Clear prescription template selection
                if (prescriptionTemplateSelect) {
                    prescriptionTemplateSelect.value = '';
                }
            } else {
                manualSection.style.display = 'none';
            }
        }
    }

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
     * Extract prescription template item data from select option
     */
    function extractPrescriptionTemplateItemData(option) {
        return {
            id: option.value,
            drugName: option.dataset.drugName || '',
            name: option.dataset.drugName || '', // For compatibility with existing code
            presentation: option.dataset.presentation || '',
            quantity: option.dataset.quantity || '',
            usageInstructions: option.dataset.usageInstructions || '',
            templateName: option.dataset.templateName || ''
        };
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
        if (!container) return;

        const suggestionsContainer = container.querySelector(`.${CONFIG.suggestionClass}`);
        if (!suggestionsContainer) return;

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
            const response = await fetch(`/outpatient-prescriptions/ajax/drug-templates/search/?q=${encodeURIComponent(query)}&limit=10`);
            
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
                type: 'template'
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
        leftContent.innerHTML = `
            <div class="suggestion-name fw-bold">${suggestion.name}</div>
            <div class="suggestion-presentation text-muted small">${suggestion.presentation}</div>
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
            if (suggestion.type === 'template') {
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
                showTemplateAppliedNotification(suggestion.name);
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
     * Enhance select with search functionality
     */
    function enhanceSelectWithSearch(select) {
        // Add search input above select for large lists
        if (select.options.length > 10) {
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.className = 'form-control mb-2';
            searchInput.placeholder = 'Buscar template...';
            
            searchInput.addEventListener('input', (e) => {
                filterSelectOptions(select, e.target.value);
            });
            
            select.parentNode.insertBefore(searchInput, select);
        }
    }

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
        cache: cache
    };

})();