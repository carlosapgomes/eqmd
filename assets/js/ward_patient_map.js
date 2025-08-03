class WardPatientMap {
    constructor() {
        this.init();
    }

    init() {
        this.bindStaticEvents();
        this.bindTreeEvents();
        this.setupSearch();
        this.setupFilters();
        this.loadStateFromSession();
    }

    bindStaticEvents() {
        // These events should only be bound once (for elements outside the tree)
        // Expand/Collapse all functionality
        document.getElementById('expand-all')?.addEventListener('click', () => {
            this.expandAll();
        });

        document.getElementById('collapse-all')?.addEventListener('click', () => {
            this.collapseAll();
        });

        // Refresh data button
        document.getElementById('refresh-data')?.addEventListener('click', () => {
            this.refreshData();
        });
    }

    bindTreeEvents() {
        // These events need to be re-bound after tree updates
        // Enhanced tree toggle with animations
        document.querySelectorAll('.ward-toggle').forEach(button => {
            button.addEventListener('click', (e) => {
                this.toggleWard(e.target.closest('.ward-toggle'));
            });
        });

        // Patient row click for quick navigation
        document.querySelectorAll('.patient-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.btn')) {
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
        const target = document.getElementById('ward-' + wardId);
        const icon = button.querySelector('i');
        const isExpanded = target.classList.contains('show');

        // Animate the transition
        if (isExpanded) {
            target.style.height = target.scrollHeight + 'px';
            target.offsetHeight; // Force reflow
            target.style.height = '0px';
            target.classList.remove('show');
            icon.classList.remove('bi-chevron-down');
            icon.classList.add('bi-chevron-right');
            button.setAttribute('aria-expanded', 'false');
        } else {
            target.style.height = '0px';
            target.classList.add('show');
            target.style.height = target.scrollHeight + 'px';
            icon.classList.remove('bi-chevron-right');
            icon.classList.add('bi-chevron-down');
            button.setAttribute('aria-expanded', 'true');
            
            // Reset height after animation
            setTimeout(() => {
                target.style.height = 'auto';
            }, 300);
        }

        // Save state
        this.saveWardState(wardId, !isExpanded);
    }

    expandAll() {
        document.querySelectorAll('.ward-toggle').forEach(button => {
            const wardId = button.dataset.ward;
            const target = document.getElementById('ward-' + wardId);
            if (!target.classList.contains('show')) {
                this.toggleWard(button);
            }
        });
    }

    collapseAll() {
        document.querySelectorAll('.ward-toggle').forEach(button => {
            const wardId = button.dataset.ward;
            const target = document.getElementById('ward-' + wardId);
            if (target.classList.contains('show')) {
                this.toggleWard(button);
            }
        });
    }

    setupSearch() {
        const searchInput = document.getElementById('patient-search');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.filterPatients(e.target.value.toLowerCase());
            }, 300);
        });
    }

    filterPatients(searchTerm) {
        const wardBranches = document.querySelectorAll('.ward-branch');
        
        wardBranches.forEach(branch => {
            const patients = branch.querySelectorAll('.patient-item');
            let hasVisiblePatients = false;

            patients.forEach(patient => {
                const patientName = patient.querySelector('.fw-medium')?.textContent?.toLowerCase() || '';
                const bedNumber = patient.querySelector('strong')?.textContent?.toLowerCase() || '';
                
                if (searchTerm === '' || 
                    patientName.includes(searchTerm) || 
                    bedNumber.includes(searchTerm)) {
                    patient.style.display = 'block';
                    hasVisiblePatients = true;
                } else {
                    patient.style.display = 'none';
                }
            });

            // Show/hide ward based on whether it has visible patients
            const wardHeader = branch.querySelector('.ward-header');
            if (searchTerm === '' || hasVisiblePatients) {
                branch.style.display = 'block';
                wardHeader.style.opacity = '1';
            } else {
                branch.style.display = 'none';
            }

            // Auto-expand wards with search results
            if (searchTerm !== '' && hasVisiblePatients) {
                const wardToggle = branch.querySelector('.ward-toggle');
                const target = branch.querySelector('.ward-patients');
                if (!target.classList.contains('show')) {
                    this.toggleWard(wardToggle);
                }
            }
        });

        this.updateSearchResults(searchTerm);
    }

    updateSearchResults(searchTerm) {
        const resultContainer = document.getElementById('search-results');
        if (!resultContainer) return;

        if (searchTerm === '') {
            resultContainer.innerHTML = '';
            return;
        }

        const visiblePatients = document.querySelectorAll('.patient-item[style*="block"], .patient-item:not([style*="none"])');
        const count = Array.from(visiblePatients).filter(p => p.style.display !== 'none').length;
        
        resultContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-search me-2"></i>
                Encontrados ${count} paciente(s) para "${searchTerm}"
                ${count === 0 ? '<br><small>Tente buscar por nome do paciente ou número do leito</small>' : ''}
            </div>
        `;
    }

    setupFilters() {
        // Ward filter
        const wardFilter = document.getElementById('ward-filter');
        wardFilter?.addEventListener('change', (e) => {
            this.filterByWard(e.target.value);
        });

        // Tag filter - commented out until implemented
        // const tagFilter = document.getElementById('tag-filter');
        // tagFilter?.addEventListener('change', (e) => {
        //     this.filterByTag(e.target.value);
        // });
    }


    filterByWard(wardId) {
        const wardBranches = document.querySelectorAll('.ward-branch');
        
        wardBranches.forEach(branch => {
            const branchWardId = branch.querySelector('.ward-toggle')?.dataset.ward;
            
            if (wardId === '' || branchWardId === wardId) {
                branch.classList.remove('filtered-out');
            } else {
                branch.classList.add('filtered-out');
            }
        });
    }

    updateWardVisibility() {
        const wardBranches = document.querySelectorAll('.ward-branch');
        
        wardBranches.forEach(branch => {
            const visiblePatients = branch.querySelectorAll('.patient-item:not(.filtered-out)');
            
            if (visiblePatients.length > 0) {
                branch.classList.remove('no-visible-patients');
            } else {
                branch.classList.add('no-visible-patients');
            }
        });
    }

    saveWardState(wardId, isExpanded) {
        const states = JSON.parse(sessionStorage.getItem('wardStates') || '{}');
        states[wardId] = isExpanded;
        sessionStorage.setItem('wardStates', JSON.stringify(states));
    }

    loadStateFromSession() {
        const states = JSON.parse(sessionStorage.getItem('wardStates') || '{}');
        
        Object.keys(states).forEach(wardId => {
            const button = document.querySelector(`[data-ward="${wardId}"]`);
            const target = document.getElementById('ward-' + wardId);
            const shouldBeExpanded = states[wardId];
            const isCurrentlyExpanded = target?.classList.contains('show');

            if (button && target && shouldBeExpanded !== isCurrentlyExpanded) {
                this.toggleWard(button);
            }
        });
    }

    // Refresh functionality for real-time updates
    async refreshData() {
        const refreshButton = document.getElementById('refresh-data');
        const originalContent = refreshButton?.innerHTML;
        
        try {
            // Show loading state
            if (refreshButton) {
                refreshButton.disabled = true;
                refreshButton.innerHTML = '<i class="bi bi-arrow-clockwise me-1 spin"></i>Atualizando...';
            }
            
            const response = await fetch(window.location.href, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const html = await response.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTreeContent = doc.querySelector('.ward-tree');
                
                if (newTreeContent) {
                    document.querySelector('.ward-tree').innerHTML = newTreeContent.innerHTML;
                    this.bindTreeEvents(); // Re-bind only tree events to new elements
                    this.loadStateFromSession(); // Restore expanded states
                    
                    // Show success feedback briefly
                    if (refreshButton) {
                        refreshButton.innerHTML = '<i class="bi bi-check-circle me-1"></i>Atualizado!';
                        setTimeout(() => {
                            refreshButton.innerHTML = originalContent;
                            refreshButton.disabled = false;
                        }, 1000);
                    }
                }
            } else {
                throw new Error('Falha na atualização');
            }
        } catch (error) {
            console.error('Failed to refresh data:', error);
            
            // Show error feedback
            if (refreshButton) {
                refreshButton.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i>Erro';
                setTimeout(() => {
                    refreshButton.innerHTML = originalContent;
                    refreshButton.disabled = false;
                }, 2000);
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new WardPatientMap();
});