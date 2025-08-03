class WardPatientMap {
    constructor() {
        this.init();
    }

    init() {
        this.bindStaticEvents();
        this.bindTreeEvents();
        this.checkIfFiltersCleared();
        this.loadStateFromSession();
    }

    bindStaticEvents() {
        document.getElementById("expand-all")?.addEventListener("click", () => {
            this.expandAll();
        });
        document.getElementById("collapse-all")?.addEventListener("click", () => {
            this.collapseAll();
        });
        document.getElementById("refresh-data")?.addEventListener("click", () => {
            this.refreshData();
        });
    }

    bindTreeEvents() {
        document.querySelectorAll(".ward-toggle").forEach((button) => {
            button.addEventListener("click", (e) => {
                this.toggleWard(e.target.closest(".ward-toggle"));
            });
        });

        document.querySelectorAll(".patient-item").forEach((item) => {
            item.addEventListener("click", (e) => {
                if (!e.target.closest(".btn")) {
                    const link = item.querySelector('a[href*="timeline"]');
                    if (link) {
                        window.location.href = link.href;
                    }
                }
            });
        });
    }

    toggleWard(button) {
        const wardId = button.dataset.ward;
        const patientsDiv = document.getElementById("ward-" + wardId);
        const icon = button.querySelector("i");
        const isExpanded = patientsDiv.classList.contains("show");

        if (isExpanded) {
            // Collapse
            patientsDiv.style.height = patientsDiv.scrollHeight + "px";
            patientsDiv.offsetHeight; // Force reflow
            patientsDiv.style.height = "0px";
            patientsDiv.classList.remove("show");
            icon.classList.remove("bi-chevron-down");
            icon.classList.add("bi-chevron-right");
            button.setAttribute("aria-expanded", "false");
        } else {
            // Expand
            patientsDiv.style.height = "0px";
            patientsDiv.classList.add("show");
            patientsDiv.style.height = patientsDiv.scrollHeight + "px";
            icon.classList.remove("bi-chevron-right");
            icon.classList.add("bi-chevron-down");
            button.setAttribute("aria-expanded", "true");
            
            // Reset height after animation
            setTimeout(() => {
                patientsDiv.style.height = "auto";
            }, 300);
        }

        this.saveWardState(wardId, !isExpanded);
    }

    expandAll() {
        document.querySelectorAll(".ward-toggle").forEach((button) => {
            const wardId = button.dataset.ward;
            const patientsDiv = document.getElementById("ward-" + wardId);
            if (!patientsDiv.classList.contains("show")) {
                this.toggleWard(button);
            }
        });
    }

    collapseAll() {
        document.querySelectorAll(".ward-toggle").forEach((button) => {
            const wardId = button.dataset.ward;
            const patientsDiv = document.getElementById("ward-" + wardId);
            if (patientsDiv.classList.contains("show")) {
                this.toggleWard(button);
            }
        });
    }

    saveWardState(wardId, isExpanded) {
        const states = JSON.parse(sessionStorage.getItem("wardStates") || "{}");
        states[wardId] = isExpanded;
        sessionStorage.setItem("wardStates", JSON.stringify(states));
    }

    checkIfFiltersCleared() {
        // Check if any filters are active by examining URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const hasActiveFilters = urlParams.get('q') || urlParams.get('ward') || urlParams.get('tag');
        
        // If no filters are active, clear ward states to return to initial state
        if (!hasActiveFilters) {
            sessionStorage.removeItem("wardStates");
        }
    }

    loadStateFromSession() {
        const states = JSON.parse(sessionStorage.getItem("wardStates") || "{}");
        Object.keys(states).forEach((wardId) => {
            const button = document.querySelector(`[data-ward="${wardId}"]`);
            const patientsDiv = document.getElementById("ward-" + wardId);
            if (button && patientsDiv) {
                const shouldBeExpanded = states[wardId];
                const isExpanded = patientsDiv.classList.contains("show");
                if (shouldBeExpanded !== isExpanded) {
                    this.toggleWard(button);
                }
            }
        });
    }

    async refreshData() {
        const button = document.getElementById("refresh-data");
        const originalHTML = button?.innerHTML;

        try {
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-arrow-clockwise me-1 spin"></i>Atualizando...';
            }

            // Simple page refresh for server-side filtering
            window.location.reload();

        } catch (error) {
            console.error("Failed to refresh data:", error);
            if (button) {
                button.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i>Erro';
                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.disabled = false;
                }, 2000);
            }
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    new WardPatientMap();
});