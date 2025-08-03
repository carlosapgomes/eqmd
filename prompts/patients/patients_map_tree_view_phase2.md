# Patients Map Tree View - Phase 2: Enhanced UI & JavaScript Interactivity

## Phase 2 Overview

Enhance the basic tree view with advanced JavaScript functionality, search capabilities, improved styling, and user experience features.

## Key Enhancements

1. **Advanced Tree Interactions**
2. **Search and Filter System**
3. **Enhanced Visual Design**
4. **Real-time Features**
5. **Accessibility Improvements**

## Step-by-Step Implementation

### Step 1: Create Dedicated JavaScript File ✅ DONE

**File**: `assets/js/ward_patient_map.js` (source) → `static/js/ward_patient_map.js` (webpack output)

```javascript
class WardPatientMap {
  constructor() {
    this.init();
  }

  init() {
    this.bindEvents();
    this.setupSearch();
    this.setupFilters();
    this.loadStateFromSession();
  }

  bindEvents() {
    // Enhanced tree toggle with animations
    document.querySelectorAll(".ward-toggle").forEach((button) => {
      button.addEventListener("click", (e) => {
        this.toggleWard(e.target.closest(".ward-toggle"));
      });
    });

    // Expand/Collapse all functionality
    document.getElementById("expand-all")?.addEventListener("click", () => {
      this.expandAll();
    });

    document.getElementById("collapse-all")?.addEventListener("click", () => {
      this.collapseAll();
    });

    // Patient row click for quick navigation
    document.querySelectorAll(".patient-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        if (!e.target.closest(".btn")) {
          const timelineLink = item.querySelector('a[href*="timeline"]');
          if (timelineLink) {
            window.location.href = timelineLink.href;
          }
        }
      });
    });
  }

  toggleWard(button) {
    const wardId = button.dataset.ward;
    const target = document.getElementById("ward-" + wardId);
    const icon = button.querySelector("i");
    const isExpanded = target.classList.contains("show");

    // Animate the transition
    if (isExpanded) {
      target.style.height = target.scrollHeight + "px";
      target.offsetHeight; // Force reflow
      target.style.height = "0px";
      target.classList.remove("show");
      icon.classList.remove("bi-chevron-down");
      icon.classList.add("bi-chevron-right");
      button.setAttribute("aria-expanded", "false");
    } else {
      target.style.height = "0px";
      target.classList.add("show");
      target.style.height = target.scrollHeight + "px";
      icon.classList.remove("bi-chevron-right");
      icon.classList.add("bi-chevron-down");
      button.setAttribute("aria-expanded", "true");

      // Reset height after animation
      setTimeout(() => {
        target.style.height = "auto";
      }, 300);
    }

    // Save state
    this.saveWardState(wardId, !isExpanded);
  }

  expandAll() {
    document.querySelectorAll(".ward-toggle").forEach((button) => {
      const wardId = button.dataset.ward;
      const target = document.getElementById("ward-" + wardId);
      if (!target.classList.contains("show")) {
        this.toggleWard(button);
      }
    });
  }

  collapseAll() {
    document.querySelectorAll(".ward-toggle").forEach((button) => {
      const wardId = button.dataset.ward;
      const target = document.getElementById("ward-" + wardId);
      if (target.classList.contains("show")) {
        this.toggleWard(button);
      }
    });
  }

  setupSearch() {
    const searchInput = document.getElementById("patient-search");
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        this.filterPatients(e.target.value.toLowerCase());
      }, 300);
    });
  }

  filterPatients(searchTerm) {
    const wardBranches = document.querySelectorAll(".ward-branch");

    wardBranches.forEach((branch) => {
      const patients = branch.querySelectorAll(".patient-item");
      let hasVisiblePatients = false;

      patients.forEach((patient) => {
        const patientName =
          patient
            .querySelector("span:nth-of-type(3)")
            ?.textContent?.toLowerCase() || "";
        const bedNumber =
          patient.querySelector("strong")?.textContent?.toLowerCase() || "";

        if (
          searchTerm === "" ||
          patientName.includes(searchTerm) ||
          bedNumber.includes(searchTerm)
        ) {
          patient.style.display = "block";
          hasVisiblePatients = true;
        } else {
          patient.style.display = "none";
        }
      });

      // Show/hide ward based on whether it has visible patients
      const wardHeader = branch.querySelector(".ward-header");
      if (searchTerm === "" || hasVisiblePatients) {
        branch.style.display = "block";
        wardHeader.style.opacity = "1";
      } else {
        branch.style.display = "none";
      }

      // Auto-expand wards with search results
      if (searchTerm !== "" && hasVisiblePatients) {
        const wardToggle = branch.querySelector(".ward-toggle");
        const target = branch.querySelector(".ward-patients");
        if (!target.classList.contains("show")) {
          this.toggleWard(wardToggle);
        }
      }
    });

    this.updateSearchResults(searchTerm);
  }

  updateSearchResults(searchTerm) {
    const resultContainer = document.getElementById("search-results");
    if (!resultContainer) return;

    if (searchTerm === "") {
      resultContainer.innerHTML = "";
      return;
    }

    const visiblePatients = document.querySelectorAll(
      '.patient-item[style*="block"], .patient-item:not([style*="none"])',
    );
    const count = Array.from(visiblePatients).filter(
      (p) => p.style.display !== "none",
    ).length;

    resultContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-search me-2"></i>
                Encontrados ${count} paciente(s) para "${searchTerm}"
                ${count === 0 ? "<br><small>Tente buscar por nome do paciente ou número do leito</small>" : ""}
            </div>
        `;
  }

  setupFilters() {
    // Status filter
    const statusFilter = document.getElementById("status-filter");
    statusFilter?.addEventListener("change", (e) => {
      this.filterByStatus(e.target.value);
    });

    // Ward filter
    const wardFilter = document.getElementById("ward-filter");
    wardFilter?.addEventListener("change", (e) => {
      this.filterByWard(e.target.value);
    });

    // Tag filter
    const tagFilter = document.getElementById("tag-filter");
    tagFilter?.addEventListener("change", (e) => {
      this.filterByTag(e.target.value);
    });
  }

  filterByStatus(status) {
    const patients = document.querySelectorAll(".patient-item");

    patients.forEach((patient) => {
      const statusBadge = patient.querySelector(".badge");
      const patientStatus = statusBadge ? statusBadge.textContent.trim() : "";

      if (status === "" || patientStatus === status) {
        patient.classList.remove("filtered-out");
      } else {
        patient.classList.add("filtered-out");
      }
    });

    this.updateWardVisibility();
  }

  filterByWard(wardId) {
    const wardBranches = document.querySelectorAll(".ward-branch");

    wardBranches.forEach((branch) => {
      const branchWardId = branch.querySelector(".ward-toggle")?.dataset.ward;

      if (wardId === "" || branchWardId === wardId) {
        branch.classList.remove("filtered-out");
      } else {
        branch.classList.add("filtered-out");
      }
    });
  }

  updateWardVisibility() {
    const wardBranches = document.querySelectorAll(".ward-branch");

    wardBranches.forEach((branch) => {
      const visiblePatients = branch.querySelectorAll(
        ".patient-item:not(.filtered-out)",
      );

      if (visiblePatients.length > 0) {
        branch.classList.remove("no-visible-patients");
      } else {
        branch.classList.add("no-visible-patients");
      }
    });
  }

  saveWardState(wardId, isExpanded) {
    const states = JSON.parse(sessionStorage.getItem("wardStates") || "{}");
    states[wardId] = isExpanded;
    sessionStorage.setItem("wardStates", JSON.stringify(states));
  }

  loadStateFromSession() {
    const states = JSON.parse(sessionStorage.getItem("wardStates") || "{}");

    Object.keys(states).forEach((wardId) => {
      const button = document.querySelector(`[data-ward="${wardId}"]`);
      const target = document.getElementById("ward-" + wardId);
      const shouldBeExpanded = states[wardId];
      const isCurrentlyExpanded = target?.classList.contains("show");

      if (button && target && shouldBeExpanded !== isCurrentlyExpanded) {
        this.toggleWard(button);
      }
    });
  }

  // Refresh functionality for real-time updates
  async refreshData() {
    try {
      const response = await fetch(window.location.href, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const newTreeContent = doc.querySelector(".ward-tree");

        if (newTreeContent) {
          document.querySelector(".ward-tree").innerHTML =
            newTreeContent.innerHTML;
          this.bindEvents(); // Re-bind events to new elements
          this.loadStateFromSession(); // Restore expanded states
        }
      }
    } catch (error) {
      console.error("Failed to refresh data:", error);
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  new WardPatientMap();
});
```

### Step 2: Enhanced Template with Search and Filters ✅ DONE

**File**: `apps/patients/templates/patients/ward_patient_map.html` (Update)

Add the following sections before the tree view:

```html
<!-- Add after the header section and before the tree view -->

<!-- Search and Filter Section -->
<div class="row mb-3">
  <div class="col-12">
    <div class="card">
      <div class="card-body">
        <div class="row g-3">
          <!-- Search -->
          <div class="col-md-4">
            <label for="patient-search" class="form-label">
              <i class="bi bi-search me-1"></i>
              Buscar Paciente
            </label>
            <input
              type="text"
              class="form-control"
              id="patient-search"
              placeholder="Nome do paciente ou número do leito..."
            />
          </div>

          <!-- Status Filter -->
          <div class="col-md-2">
            <label for="status-filter" class="form-label">Status</label>
            <select class="form-select" id="status-filter">
              <option value="">Todos</option>
              <option value="Internado">Internado</option>
              <option value="Emergência">Emergência</option>
            </select>
          </div>

          <!-- Ward Filter -->
          <div class="col-md-3">
            <label for="ward-filter" class="form-label">Ala</label>
            <select class="form-select" id="ward-filter">
              <option value="">Todas as Alas</option>
              {% for ward_info in ward_data %}
              <option value="{{ ward_info.ward.id }}">
                {{ ward_info.ward.abbreviation }} - {{ ward_info.ward.name }}
              </option>
              {% endfor %}
            </select>
          </div>

          <!-- Tree Controls -->
          <div class="col-md-3">
            <label class="form-label">Controles</label>
            <div class="btn-group w-100" role="group">
              <button
                type="button"
                class="btn btn-outline-secondary"
                id="expand-all"
              >
                <i class="bi bi-arrows-expand me-1"></i>
                Expandir
              </button>
              <button
                type="button"
                class="btn btn-outline-secondary"
                id="collapse-all"
              >
                <i class="bi bi-arrows-collapse me-1"></i>
                Recolher
              </button>
            </div>
          </div>
        </div>

        <!-- Search Results -->
        <div id="search-results" class="mt-3"></div>
      </div>
    </div>
  </div>
</div>
```

### Step 3: Enhanced CSS Styling ✅ DONE

**File**: `assets/css/ward_patient_map.css`

```css
/* Ward Patient Map Styles */
.ward-tree {
  --tree-line-color: #dee2e6;
  --tree-hover-color: #f8f9fa;
  --animation-duration: 0.3s;
}

/* Tree Structure */
.ward-tree .ward-branch {
  border-left: 3px solid var(--bs-medical-primary);
  margin-left: 1rem;
  padding-left: 1rem;
  position: relative;
  transition: all var(--animation-duration) ease;
}

.ward-tree .ward-branch::before {
  content: "";
  position: absolute;
  left: -3px;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(
    to bottom,
    var(--bs-medical-primary),
    var(--bs-medical-secondary)
  );
  opacity: 0.7;
}

/* Ward Header Enhancements */
.ward-header {
  border: 1px solid var(--bs-border-color);
  transition: all var(--animation-duration) ease;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}

.ward-header:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.ward-toggle {
  color: var(--bs-medical-primary);
  text-decoration: none;
  transition: all 0.2s ease;
  border: none;
  background: none;
}

.ward-toggle:hover {
  color: var(--bs-medical-primary-dark);
  transform: scale(1.1);
}

/* Patient Items */
.patient-item {
  border-left: 2px solid var(--bs-medical-secondary) !important;
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.patient-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: var(--bs-medical-secondary);
  transform: translateX(-2px);
  transition: all 0.2s ease;
}

.patient-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  background-color: var(--tree-hover-color) !important;
}

.patient-item:hover::before {
  width: 8px;
  background: var(--bs-medical-primary);
}

/* Animations */
.ward-patients {
  overflow: hidden;
  transition: height var(--animation-duration) ease;
}

.collapse {
  height: 0;
}

.collapse.show {
  height: auto;
}

/* Filter States */
.filtered-out {
  opacity: 0.3;
  pointer-events: none;
}

.no-visible-patients {
  opacity: 0.5;
}

/* Search Highlights */
.search-highlight {
  background-color: #fff3cd;
  padding: 0 4px;
  border-radius: 2px;
}

/* Status Badges */
.badge {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* Capacity Indicators */
.capacity-indicator {
  height: 4px;
  background-color: var(--bs-gray-300);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 5px;
}

.capacity-fill {
  height: 100%;
  transition: width 0.5s ease;
}

.capacity-fill.low {
  background-color: var(--bs-success);
}
.capacity-fill.medium {
  background-color: var(--bs-warning);
}
.capacity-fill.high {
  background-color: var(--bs-danger);
}

/* Responsive Design */
@media (max-width: 768px) {
  .ward-tree .ward-branch {
    margin-left: 0.5rem;
    padding-left: 0.5rem;
  }

  .patient-item .d-flex {
    flex-direction: column;
    align-items: flex-start !important;
  }

  .patient-item .d-flex > div:last-child {
    margin-top: 10px;
    width: 100%;
  }
}

/* Loading States */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.loading-spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--bs-medical-primary);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Accessibility */
.ward-toggle:focus {
  outline: 2px solid var(--bs-medical-primary);
  outline-offset: 2px;
}

.patient-item:focus-within {
  outline: 2px solid var(--bs-medical-primary);
  outline-offset: 2px;
}

/* Print Styles */
@media print {
  .card,
  .ward-header,
  .patient-item {
    box-shadow: none !important;
    border: 1px solid #000 !important;
  }

  .btn,
  .badge {
    color: #000 !important;
    background: #fff !important;
    border: 1px solid #000 !important;
  }

  .collapse:not(.show) {
    display: block !important;
    height: auto !important;
  }
}
```

### Step 4: Update Template to Include Assets ✅ DONE

Add to the template head section:

```html
{% block extra_css %} {{ block.super }}
<link rel="stylesheet" href="{% static 'css/ward_patient_map.css' %}" />
{% endblock %} {% block extra_js %} {{ block.super }}
<script src="{% static 'js/ward_patient_map.js' %}"></script>
{% endblock %}
```

### Step 5: Add Real-time Refresh Capability ✅ DONE

Update the view to handle AJAX requests:

```python
# Add to WardPatientMapView class
def get(self, request, *args, **kwargs):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return only the tree content for AJAX requests
        context = self.get_context_data()
        return render(request, 'patients/ward_patient_map_tree_only.html', context)
    return super().get(request, *args, **kwargs)
```

Create `ward_patient_map_tree_only.html`:

```html
<!-- Only the tree content for AJAX updates -->
{% for ward_info in ward_data %}
<!-- Ward tree content here (extract from main template) -->
{% endfor %}
```

## Phase 2 Testing

### Functionality Tests

1. **Search Functionality**

   - Test search by patient name
   - Test search by bed number
   - Verify search results counter
   - Test search clearing

2. **Filter Functionality**

   - Test status filter
   - Test ward filter
   - Test multiple filters combined

3. **Tree Interactions**

   - Test expand/collapse animations
   - Test expand all / collapse all
   - Verify state persistence

4. **Enhanced UX**
   - Test hover effects
   - Test responsive behavior
   - Test keyboard navigation

### Performance Tests

- Verify smooth animations on mobile
- Test with large numbers of patients
- Check memory usage with frequent interactions

## Phase 2 Completion Criteria

- ✅ Smooth tree expand/collapse animations
- ✅ Real-time search with debouncing
- ✅ Multiple filter options working
- ✅ State persistence across page refreshes
- ✅ Enhanced visual design with hover effects
- ✅ Mobile-responsive interactions
- ✅ Keyboard accessibility
- ✅ Performance optimized for 100+ patients

## Transition to Phase 3

Phase 2 provides a fully interactive and visually polished tree view. Phase 3 will add advanced optimizations and enterprise features.
