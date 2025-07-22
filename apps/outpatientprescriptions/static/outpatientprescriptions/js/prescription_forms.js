/**
 * Prescription Forms JavaScript
 * Handles dynamic form management for prescription items and drug template integration
 */

(function () {
  "use strict";

  // Configuration
  const CONFIG = {
    formsetPrefix: "items",
    addButtonClass: "add-item-btn",
    removeButtonClass: "remove-item-btn",
    formContainerClass: "prescription-item-form",
    templateSelectClass: "drug-template-select",
    emptyFormSelector: "#empty-form-template",
    formsetContainerSelector: "#prescription-items-container",
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
      console.warn("Prescription formset container not found");
      return;
    }

    addButton = document.getElementById("add-item-btn");
    totalFormsInput = document.querySelector(
      `#id_${CONFIG.formsetPrefix}-TOTAL_FORMS`,
    );
    emptyForm = document.querySelector(CONFIG.emptyFormSelector);

    if (!totalFormsInput || !emptyForm) {
      console.warn("Required formset elements not found");
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

    console.log("Prescription forms initialized");
  }

  /**
   * Bind event listeners
   */
  function bindEvents() {
    // Add item button
    if (addButton) {
      addButton.addEventListener("click", addPrescriptionItem);
    }

    // Remove item buttons (delegated)
    formsetContainer.addEventListener("click", function (e) {
      if (
        e.target.classList.contains(CONFIG.removeButtonClass) ||
        e.target.closest(`.${CONFIG.removeButtonClass}`)
      ) {
        const removeBtn = e.target.classList.contains(CONFIG.removeButtonClass)
          ? e.target
          : e.target.closest(`.${CONFIG.removeButtonClass}`);
        removePrescriptionItem(removeBtn);
      }
    });

    // Drug template selection (delegated)
    formsetContainer.addEventListener("change", function (e) {
      if (e.target.classList.contains(CONFIG.templateSelectClass)) {
        handleTemplateSelection(e.target);
      }
    });

    // Arrow button clicks for reordering
    formsetContainer.addEventListener("click", function(e) {
      if (e.target.classList.contains('move-up-btn') || e.target.closest('.move-up-btn')) {
        const moveBtn = e.target.classList.contains('move-up-btn') ? e.target : e.target.closest('.move-up-btn');
        moveFormUp(moveBtn);
      } else if (e.target.classList.contains('move-down-btn') || e.target.closest('.move-down-btn')) {
        const moveBtn = e.target.classList.contains('move-down-btn') ? e.target : e.target.closest('.move-down-btn');
        moveFormDown(moveBtn);
      }
    });
  }

  /**
   * Initialize existing forms with proper event handling
   */
  function initializeExistingForms() {
    const existingForms = formsetContainer.querySelectorAll(
      `.${CONFIG.formContainerClass}`,
    );
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
    const newFormWrapper = document.createElement("div");
    newFormWrapper.innerHTML = newFormHtml;
    const newForm = newFormWrapper.firstElementChild;

    // Mark order input as new form for auto-numbering
    const orderInput = newForm.querySelector('input[name$="-order"]');
    if (orderInput) {
      orderInput.setAttribute('data-new-form', 'true');
    }

    // Update form numbering
    const formTitle = newForm.querySelector("h6");
    if (formTitle) {
      formTitle.innerHTML = `<i class="bi bi-pill me-1"></i>Medicamento ${formIndex + 1}`;
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
    return newForm; // Return the newly created form
  }

  /**
   * Remove a prescription item form
   */
  function removePrescriptionItem(removeButton) {
    const form = removeButton.closest(`.${CONFIG.formContainerClass}`);
    if (!form) return;

    // Allow removing all forms - validation will be handled at submission
    // Mark form for deletion
    const deleteInput = form.querySelector('input[name$="-DELETE"]');
    if (deleteInput) {
      deleteInput.checked = true;
      form.style.display = "none";
    } else {
      // Remove form entirely if it's new
      form.remove();
      formIndex--;
      totalFormsInput.value = formIndex;
    }

    // Update form order
    updateFormOrder();

    console.log("Removed prescription item form");
  }

  /**
   * Add remove button to a form
   */
  function addRemoveButton(form) {
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = `btn btn-outline-danger btn-sm ${CONFIG.removeButtonClass}`;
    removeButton.innerHTML = '<i class="fas fa-trash"></i> Remover';

    // Find a good place to insert the button
    const formActions = form.querySelector(".form-actions");
    if (formActions) {
      formActions.appendChild(removeButton);
    } else {
      // Create form actions container
      const actionsDiv = document.createElement("div");
      actionsDiv.className = "form-actions mt-2 text-end";
      actionsDiv.appendChild(removeButton);
      form.appendChild(actionsDiv);
    }
  }

  /**
   * Setup events for a specific form
   */
  function setupFormEvents(form, index) {
    // Remove buttons are now handled in HTML templates
    // No need to add them dynamically

    // Setup drug template selection
    const templateSelect = form.querySelector(`.${CONFIG.templateSelectClass}`);
    if (templateSelect) {
      templateSelect.addEventListener("change", () =>
        handleTemplateSelection(templateSelect),
      );
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
      presentation: selectedOption.dataset.presentation || "",
      usageInstructions: selectedOption.dataset.usageInstructions || "",
    };

    // Fill form fields
    fillFormFromTemplate(form, templateData);

    console.log("Applied drug template:", templateData.name);
  }

  /**
   * Fill form fields from drug template data
   */
  function fillFormFromTemplate(form, templateData) {
    const drugNameInput = form.querySelector('input[name$="-drug_name"]');
    const presentationInput = form.querySelector(
      'input[name$="-presentation"]',
    );
    const usageInstructionsTextarea = form.querySelector(
      'textarea[name$="-usage_instructions"]',
    );

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
   * Move form up in the list
   */
  function moveFormUp(moveButton) {
    const form = moveButton.closest(`.${CONFIG.formContainerClass}`);
    const previousForm = form.previousElementSibling;
    
    if (previousForm && previousForm.classList.contains(CONFIG.formContainerClass)) {
      formsetContainer.insertBefore(form, previousForm);
      updateAllOrderNumbers();
      console.log('Moved form up');
    }
  }

  /**
   * Move form down in the list
   */
  function moveFormDown(moveButton) {
    const form = moveButton.closest(`.${CONFIG.formContainerClass}`);
    const nextForm = form.nextElementSibling;
    
    if (nextForm && nextForm.classList.contains(CONFIG.formContainerClass)) {
      formsetContainer.insertBefore(nextForm, form);
      updateAllOrderNumbers();
      console.log('Moved form down');
    }
  }

  /**
   * Update order numbers for all forms based on their current DOM position
   */
  function updateAllOrderNumbers() {
    const visibleForms = formsetContainer.querySelectorAll(
      `.${CONFIG.formContainerClass}:not([style*="display: none"])`
    );

    visibleForms.forEach((form, index) => {
      const orderInput = form.querySelector('input[name$="-order"]');
      const formTitle = form.querySelector("h6");
      
      if (orderInput) {
        orderInput.value = index + 1;
      }
      
      if (formTitle) {
        formTitle.innerHTML = `<i class="bi bi-pill me-1"></i>Medicamento ${index + 1}`;
      }
    });
  }

  /**
   * Update form order numbers (simplified - just renumber all)
   */
  function updateFormOrder() {
    updateAllOrderNumbers();
  }

  /**
   * Load drug template data via AJAX
   */
  function loadDrugTemplateData() {
    // This function can be extended to load template data dynamically
    const templateSelects = document.querySelectorAll(
      `.${CONFIG.templateSelectClass}`,
    );

    templateSelects.forEach((select) => {
      // Enhance options with data attributes
      Array.from(select.options).forEach((option) => {
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
    const visibleForms = formsetContainer.querySelectorAll(
      `.${CONFIG.formContainerClass}:not([style*="display: none"])`,
    );

    if (visibleForms.length === 0) {
      showEmptyDrugListModal();
      return false;
    }

    // Additional validation can be added here
    return true;
  }

  /**
   * Show context-aware modal for empty drug list
   */
  function showEmptyDrugListModal() {
    // Detect if we're in create or update mode
    const isUpdateMode =
      document.querySelector('input[name="status"][type="radio"]') !== null;
    const patientTimelineUrl = getPatientTimelineUrl();

    let modalContent, actionButtons;

    if (isUpdateMode) {
      // Update mode: offer continue editing or delete prescription
      modalContent = `
                <p><strong>Esta receita não possui nenhum medicamento.</strong></p>
                <p>Você pode continuar editando para adicionar medicamentos ou remover esta receita.</p>
            `;
      actionButtons = `
                <button type="button" class="btn btn-primary" onclick="closeEmptyDrugModal()">
                    <i class="bi bi-pencil me-1"></i>
                    Continuar Editando
                </button>
                <button type="button" class="btn btn-danger" onclick="deletePrescription()">
                    <i class="bi bi-trash me-1"></i>
                    Remover Receita
                </button>
                <button type="button" class="btn btn-secondary" onclick="goToPatientTimeline()">
                    <i class="bi bi-arrow-left me-1"></i>
                    Voltar ao Timeline
                </button>
            `;
    } else {
      // Create mode: offer continue editing or return to timeline
      modalContent = `
                <p><strong>Esta receita não possui nenhum medicamento.</strong></p>
                <p>Você pode continuar editando para adicionar medicamentos ou retornar ao timeline do paciente.</p>
            `;
      actionButtons = `
                <button type="button" class="btn btn-primary" onclick="closeEmptyDrugModal()">
                    <i class="bi bi-pencil me-1"></i>
                    Continuar Editando
                </button>
                <button type="button" class="btn btn-secondary" onclick="goToPatientTimeline()">
                    <i class="bi bi-arrow-left me-1"></i>
                    Voltar ao Timeline
                </button>
            `;
    }

    // Create and show modal
    const modalHtml = `
            <div class="modal fade" id="emptyDrugListModal" tabindex="-1" aria-labelledby="emptyDrugListModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="emptyDrugListModalLabel">
                                <i class="bi bi-exclamation-triangle text-warning me-2"></i>
                                Receita sem Medicamentos
                            </h5>
                        </div>
                        <div class="modal-body">
                            ${modalContent}
                        </div>
                        <div class="modal-footer">
                            ${actionButtons}
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Remove existing modal if present
    const existingModal = document.getElementById("emptyDrugListModal");
    if (existingModal) {
      existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML("beforeend", modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(
      document.getElementById("emptyDrugListModal"),
    );
    modal.show();
  }

  /**
   * Get patient timeline URL from page context
   */
  function getPatientTimelineUrl() {
    // Try to find timeline URL from breadcrumb or back button
    const timelineLink = document.querySelector(
      'a[href*="patient_events_timeline"]',
    );
    return timelineLink ? timelineLink.href : null;
  }

  /**
   * Close the empty drug list modal
   */
  window.closeEmptyDrugModal = function () {
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("emptyDrugListModal"),
    );
    if (modal) {
      modal.hide();
    }
  };

  /**
   * Navigate to patient timeline
   */
  window.goToPatientTimeline = function () {
    const timelineUrl = getPatientTimelineUrl();
    if (timelineUrl) {
      window.location.href = timelineUrl;
    } else {
      // Fallback - try to find cancel button URL
      const cancelButton = document.querySelector(
        'a.btn-outline-secondary[href*="timeline"], a[href*="patient_events_timeline"]',
      );
      if (cancelButton) {
        window.location.href = cancelButton.href;
      } else {
        // Last resort - go back
        window.history.back();
      }
    }
  };

  /**
   * Delete prescription (for update mode)
   */
  window.deletePrescription = function () {
    // Close the empty drug modal first
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("emptyDrugListModal"),
    );
    if (modal) {
      modal.hide();
    }

    // Check if delete modal exists (should exist in update template)
    const deleteModal = document.getElementById("deleteModal");
    if (deleteModal) {
      // Use the existing delete modal for consistency
      const deleteModalInstance = new bootstrap.Modal(deleteModal);
      deleteModalInstance.show();
    } else {
      // Fallback: direct POST to delete endpoint
      const prescriptionId = getPrescriptionId();
      if (prescriptionId) {
        const deleteUrl = window.location.pathname.replace("/edit/", "/delete/");
        
        // Create a form and submit it directly
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = deleteUrl;
        
        // Add CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
          const csrfInput = document.createElement('input');
          csrfInput.type = 'hidden';
          csrfInput.name = 'csrfmiddlewaretoken';
          csrfInput.value = csrfToken.value;
          form.appendChild(csrfInput);
        }
        
        document.body.appendChild(form);
        form.submit();
      } else {
        alert("Erro: Não foi possível determinar o ID da receita para exclusão.");
      }
    }
  };

  /**
   * Get prescription ID from URL
   */
  function getPrescriptionId() {
    const pathParts = window.location.pathname.split("/");
    // Look for UUID pattern in URL
    const uuidPattern =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    for (const part of pathParts) {
      if (uuidPattern.test(part)) {
        return part;
      }
    }
    return null;
  }

  /**
   * Initialize when DOM is ready
   */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializePrescriptionForms);
  } else {
    initializePrescriptionForms();
  }

  // Expose public API
  window.PrescriptionForms = {
    initialize: initializePrescriptionForms,
    addItem: addPrescriptionItem,
    validate: validateFormset,
  };
})();

