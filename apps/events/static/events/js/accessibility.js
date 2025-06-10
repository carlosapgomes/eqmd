// Accessibility enhancements for timeline
document.addEventListener('DOMContentLoaded', function() {
    initializeKeyboardNavigation();
    initializeScreenReaderSupport();
    initializeFocusManagement();
});

function initializeKeyboardNavigation() {
    // Arrow key navigation through timeline cards
    const timelineCards = document.querySelectorAll('.timeline-card');
    let currentIndex = -1;
    
    document.addEventListener('keydown', function(e) {
        if (e.target.closest('.timeline-events')) {
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    navigateToCard(currentIndex + 1);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    navigateToCard(currentIndex - 1);
                    break;
                case 'Home':
                    e.preventDefault();
                    navigateToCard(0);
                    break;
                case 'End':
                    e.preventDefault();
                    navigateToCard(timelineCards.length - 1);
                    break;
                case 'Enter':
                case ' ':
                    if (currentIndex >= 0) {
                        e.preventDefault();
                        const card = timelineCards[currentIndex];
                        const viewLink = card.querySelector('.btn-outline-primary');
                        if (viewLink) viewLink.click();
                    }
                    break;
            }
        }
    });
    
    function navigateToCard(index) {
        if (index < 0 || index >= timelineCards.length) return;
        
        currentIndex = index;
        const card = timelineCards[index];
        
        // Remove previous focus
        timelineCards.forEach(c => c.classList.remove('keyboard-focused'));
        
        // Add focus to current card
        card.classList.add('keyboard-focused');
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Announce to screen readers
        const eventType = card.querySelector('.event-type-badge').textContent.trim();
        const timestamp = card.querySelector('time').textContent.trim();
        announceToScreenReader(`Evento ${index + 1} de ${timelineCards.length}: ${eventType}, ${timestamp}`);
    }
}

function initializeScreenReaderSupport() {
    // Live region for filter updates
    const liveRegion = document.getElementById('filter-live-region') || createLiveRegion();
    
    // Announce filter changes
    const filterInputs = document.querySelectorAll('#timeline-filters input, #timeline-filters select');
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            const filterType = this.name;
            const filterValue = this.type === 'checkbox' ? 
                (this.checked ? this.nextElementSibling.textContent : 'removido') :
                this.value || 'todos';
            
            setTimeout(() => {
                announceToScreenReader(`Filtro ${filterType}: ${filterValue}`);
            }, 100);
        });
    });
}

function createLiveRegion() {
    const liveRegion = document.createElement('div');
    liveRegion.id = 'filter-live-region';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'visually-hidden';
    document.body.appendChild(liveRegion);
    return liveRegion;
}

function announceToScreenReader(message) {
    const liveRegion = document.getElementById('filter-live-region');
    if (liveRegion) {
        liveRegion.textContent = message;
        setTimeout(() => {
            liveRegion.textContent = '';
        }, 1000);
    }
}

function initializeFocusManagement() {
    // Skip links
    const skipLink = document.querySelector('.visually-hidden-focusable');
    if (skipLink) {
        skipLink.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.focus();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Modal focus management
    const eventModal = document.getElementById('eventModal');
    if (eventModal) {
        eventModal.addEventListener('shown.bs.modal', function() {
            const firstFocusable = this.querySelector('button, input, select, textarea, a[href]');
            if (firstFocusable) firstFocusable.focus();
        });
        
        eventModal.addEventListener('hidden.bs.modal', function() {
            // Return focus to the trigger element
            const trigger = document.querySelector('[data-event-modal]:focus-within');
            if (trigger) trigger.focus();
        });
    }
}

// CSS for keyboard focus indication
const focusStyles = document.createElement('style');
focusStyles.textContent = `
    .keyboard-focused {
        outline: 3px solid #0d6efd;
        outline-offset: 2px;
        z-index: 10;
        position: relative;
    }
    
    .timeline-card:focus-within {
        outline: 2px solid #0d6efd;
        outline-offset: 1px;
    }
    
    .visually-hidden-focusable:focus {
        position: static !important;
        width: auto !important;
        height: auto !important;
        clip: auto !important;
        white-space: normal !important;
        background-color: #007bff;
        color: white;
        padding: 0.5rem;
        text-decoration: none;
        border-radius: 0.25rem;
    }
`;
document.head.appendChild(focusStyles);