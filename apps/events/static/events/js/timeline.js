// Timeline interactions and modal handling
document.addEventListener('DOMContentLoaded', function() {
    
    // Event modal handling
    const eventModal = document.getElementById('eventModal');
    if (eventModal) {
        initializeEventModal();
    }
    
    // Timeline filter handling
    initializeTimelineFilters();
    
    // Infinite scroll (optional)
    initializeInfiniteScroll();
});

function initializeEventModal() {
    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    
    // Handle event card clicks for modal
    document.addEventListener('click', function(e) {
        const modalTrigger = e.target.closest('[data-event-modal]');
        if (modalTrigger) {
            e.preventDefault();
            const eventId = modalTrigger.dataset.eventModal;
            loadEventModal(eventId);
        }
    });
}

function loadEventModal(eventId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById('eventModal'));
    const modalElement = document.getElementById('eventModal');
    
    // Show loading state
    modalElement.querySelector('#modal-loading').style.display = 'block';
    modalElement.querySelector('#modal-content').style.display = 'none';
    modalElement.querySelector('#modal-view-full').style.display = 'none';
    modalElement.querySelector('#modal-edit').style.display = 'none';
    
    // Show modal
    modal.show();
    
    // Fetch event data
    fetch(`/events/${eventId}/api/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Event not found');
            }
            return response.json();
        })
        .then(data => {
            populateEventModal(data);
        })
        .catch(error => {
            console.error('Error loading event:', error);
            showModalError('Erro ao carregar evento');
        });
}

function populateEventModal(eventData) {
    const modalElement = document.getElementById('eventModal');
    
    // Hide loading, show content
    modalElement.querySelector('#modal-loading').style.display = 'none';
    modalElement.querySelector('#modal-content').style.display = 'block';
    
    // Populate data
    modalElement.querySelector('#modal-event-type').textContent = eventData.event_type_display;
    modalElement.querySelector('#modal-datetime').textContent = eventData.created_at_formatted;
    modalElement.querySelector('#modal-creator').textContent = eventData.created_by_name;
    modalElement.querySelector('#modal-event-content').innerHTML = eventData.content || eventData.description || 'Sem conteúdo';
    
    // Updated info
    if (eventData.updated_at !== eventData.created_at) {
        const updatedElement = modalElement.querySelector('#modal-updated');
        updatedElement.style.display = 'block';
        updatedElement.querySelector('span').textContent = `Última edição: ${eventData.updated_at_formatted}`;
    }
    
    // Action buttons
    const viewFullBtn = modalElement.querySelector('#modal-view-full');
    const editBtn = modalElement.querySelector('#modal-edit');
    
    viewFullBtn.href = eventData.detail_url;
    viewFullBtn.style.display = 'inline-block';
    
    if (eventData.can_edit) {
        editBtn.href = eventData.edit_url;
        editBtn.style.display = 'inline-block';
    }
}

function showModalError(message) {
    const modalElement = document.getElementById('eventModal');
    modalElement.querySelector('#modal-loading').style.display = 'none';
    modalElement.querySelector('#modal-content').innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            ${message}
        </div>
    `;
    modalElement.querySelector('#modal-content').style.display = 'block';
}

function initializeTimelineFilters() {
    const filterForm = document.getElementById('timeline-filters');
    if (!filterForm) return;
    
    // Auto-submit on filter changes
    const filterInputs = filterForm.querySelectorAll('input[type="checkbox"], input[type="radio"], select');
    
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Add loading indicator
            showFilterLoading();
            
            // Debounce for better UX
            setTimeout(() => {
                filterForm.submit();
            }, 300);
        });
    });
    
    // Date input handling
    const dateInputs = filterForm.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Clear quick date selection
            const quickDateInputs = filterForm.querySelectorAll('input[name="quick_date"]');
            quickDateInputs.forEach(radio => {
                if (radio.value !== '') {
                    radio.checked = false;
                }
            });
        });
    });
    
    // Quick date handling
    const quickDateInputs = filterForm.querySelectorAll('input[name="quick_date"]');
    quickDateInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value !== '') {
                const dateInputs = filterForm.querySelectorAll('input[type="date"]');
                dateInputs.forEach(dateInput => {
                    dateInput.value = '';
                });
            }
        });
    });
}

function showFilterLoading() {
    const timelineContainer = document.querySelector('.timeline-events');
    if (timelineContainer) {
        timelineContainer.style.opacity = '0.6';
        timelineContainer.style.pointerEvents = 'none';
        
        // Add loading spinner if not exists
        if (!document.querySelector('.filter-loading')) {
            const loading = document.createElement('div');
            loading.className = 'filter-loading position-absolute top-50 start-50 translate-middle';
            loading.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            `;
            timelineContainer.parentElement.style.position = 'relative';
            timelineContainer.parentElement.appendChild(loading);
        }
    }
}

function initializeInfiniteScroll() {
    const nextPageUrl = document.querySelector('[data-next-page]')?.dataset.nextPage;
    if (!nextPageUrl) return;
    
    const options = {
        root: null,
        rootMargin: '100px',
        threshold: 0.1
    };
    
    const loadMore = document.createElement('div');
    loadMore.className = 'load-more-trigger';
    loadMore.style.height = '1px';
    
    const timelineContainer = document.querySelector('.timeline-events');
    if (timelineContainer) {
        timelineContainer.appendChild(loadMore);
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadMoreEvents(nextPageUrl);
                    observer.unobserve(entry.target);
                }
            });
        }, options);
        
        observer.observe(loadMore);
    }
}

function loadMoreEvents(url) {
    // Implementation for infinite scroll loading
    // This would fetch the next page and append to the timeline
    console.log('Loading more events from:', url);
}