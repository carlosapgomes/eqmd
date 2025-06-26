/**
 * PhotoSeries JavaScript Functionality
 * Handles carousel navigation, photo controls, and interactions
 */

window.PhotoSeries = (function() {
    'use strict';
    
    let currentPhotoIndex = 0;
    let totalPhotos = 0;
    let photos = [];
    let carousel = null;
    let isFullscreen = false;
    let zoomLevel = 1;
    let isDragging = false;
    let dragStart = { x: 0, y: 0 };
    let imagePosition = { x: 0, y: 0 };
    
    // DOM elements
    let carouselElement = null;
    let photoInfoPanel = null;
    let photoCounter = null;
    let photoMetadata = null;
    
    /**
     * Initialize PhotoSeries functionality
     */
    function init() {
        // Load photos data from script tag
        loadPhotosData();
        
        // Initialize carousel
        initializeCarousel();
        
        // Initialize photo controls
        initializePhotoControls();
        
        // Initialize keyboard navigation
        initializeKeyboardNavigation();
        
        // Initialize responsive handling
        initializeResponsiveHandling();
        
        console.log('PhotoSeries initialized with', totalPhotos, 'photos');
    }
    
    /**
     * Load photos data from JSON script tag
     */
    function loadPhotosData() {
        const dataScript = document.getElementById('photoSeriesData');
        if (dataScript) {
            try {
                const data = JSON.parse(dataScript.textContent);
                photos = data.photos || [];
                totalPhotos = photos.length;
                currentPhotoIndex = 0;
                
                console.log('Loaded photos data:', photos);
            } catch (e) {
                console.error('Error parsing photos data:', e);
                photos = [];
                totalPhotos = 0;
            }
        }
    }
    
    /**
     * Initialize Bootstrap carousel
     */
    function initializeCarousel() {
        carouselElement = document.getElementById('photoCarousel');
        photoInfoPanel = document.getElementById('photoInfoPanel');
        photoCounter = document.getElementById('photoCounter');
        photoMetadata = document.getElementById('photoMetadata');
        
        if (carouselElement) {
            // Initialize Bootstrap carousel
            carousel = new bootstrap.Carousel(carouselElement, {
                interval: false, // Disable auto-advance
                wrap: true,
                keyboard: true
            });
            
            // Listen for carousel slide events
            carouselElement.addEventListener('slide.bs.carousel', handleCarouselSlide);
            carouselElement.addEventListener('slid.bs.carousel', handleCarouselSlid);
            
            // Update initial photo info
            updatePhotoInfo(currentPhotoIndex);
            updateNavigationButtons();
        }
    }
    
    /**
     * Initialize photo control buttons
     */
    function initializePhotoControls() {
        // Zoom controls
        const zoomInBtn = document.getElementById('zoomInBtn');
        const zoomOutBtn = document.getElementById('zoomOutBtn');
        const originalSizeBtn = document.getElementById('originalSizeBtn');
        const fullPageBtn = document.getElementById('fullPageBtn');
        
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => zoomPhoto(1.2));
        }
        
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => zoomPhoto(0.8));
        }
        
        if (originalSizeBtn) {
            originalSizeBtn.addEventListener('click', resetZoom);
        }
        
        if (fullPageBtn) {
            fullPageBtn.addEventListener('click', toggleFullscreen);
        }
        
        // Download button
        const downloadBtn = document.getElementById('downloadCurrentBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', downloadCurrentPhoto);
        }
        
        // Custom navigation buttons
        const prevPhotoBtn = document.getElementById('prevPhotoBtn');
        const nextPhotoBtn = document.getElementById('nextPhotoBtn');
        
        if (prevPhotoBtn) {
            prevPhotoBtn.addEventListener('click', previousPhoto);
        }
        
        if (nextPhotoBtn) {
            nextPhotoBtn.addEventListener('click', nextPhoto);
        }
        
        // Initialize image dragging for zoomed photos
        initializeImageDragging();
    }
    
    /**
     * Initialize keyboard navigation
     */
    function initializeKeyboardNavigation() {
        document.addEventListener('keydown', function(e) {
            // Only handle keys when not in an input field
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    previousPhoto();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    nextPhoto();
                    break;
                case '+':
                case '=':
                    e.preventDefault();
                    zoomPhoto(1.2);
                    break;
                case '-':
                    e.preventDefault();
                    zoomPhoto(0.8);
                    break;
                case '0':
                    e.preventDefault();
                    resetZoom();
                    break;
                case 'f':
                case 'F':
                    e.preventDefault();
                    toggleFullscreen();
                    break;
                case 'Escape':
                    if (isFullscreen) {
                        e.preventDefault();
                        exitFullscreen();
                    }
                    break;
            }
        });
    }
    
    /**
     * Initialize responsive handling
     */
    function initializeResponsiveHandling() {
        // Handle window resize
        window.addEventListener('resize', handleWindowResize);
        
        // Handle orientation change on mobile
        window.addEventListener('orientationchange', function() {
            setTimeout(handleWindowResize, 100);
        });
    }
    
    /**
     * Handle carousel slide start
     */
    function handleCarouselSlide(event) {
        // Reset zoom when changing photos
        resetZoom();
    }
    
    /**
     * Handle carousel slide complete
     */
    function handleCarouselSlid(event) {
        // Update current index from carousel
        const activeItem = carouselElement.querySelector('.carousel-item.active');
        if (activeItem) {
            const index = parseInt(activeItem.dataset.photoIndex) || 0;
            currentPhotoIndex = index;
            updatePhotoInfo(currentPhotoIndex);
            updateNavigationButtons();
        }
    }
    
    /**
     * Update photo information panel
     */
    function updatePhotoInfo(index) {
        if (index < 0 || index >= photos.length) return;
        
        const photo = photos[index];
        
        // Update counters
        const photoCounter = document.getElementById('photoCounter');
        const currentPhotoIndexSpan = document.getElementById('currentPhotoIndex');
        
        if (photoCounter) {
            photoCounter.textContent = `${index + 1} de ${totalPhotos}`;
        }
        
        if (currentPhotoIndexSpan) {
            currentPhotoIndexSpan.textContent = index + 1;
        }
        
        // Update metadata
        if (photoMetadata && photo) {
            updatePhotoMetadata(photo);
        }
        
        // Update download link
        const downloadBtn = document.getElementById('downloadCurrentBtn');
        if (downloadBtn && photo.downloadUrl) {
            downloadBtn.href = photo.downloadUrl;
        }
    }
    
    /**
     * Update navigation button states
     */
    function updateNavigationButtons() {
        const prevBtn = document.getElementById('prevPhotoBtn');
        const nextBtn = document.getElementById('nextPhotoBtn');
        
        if (prevBtn) {
            prevBtn.disabled = currentPhotoIndex <= 0;
        }
        
        if (nextBtn) {
            nextBtn.disabled = currentPhotoIndex >= totalPhotos - 1;
        }
    }
    
    /**
     * Update photo metadata display
     */
    function updatePhotoMetadata(photo) {
        if (!photoMetadata) return;
        
        const metadataHTML = `
            <div class="metadata-item">
                <span class="metadata-label">
                    <i class="bi bi-file-earmark-text me-1"></i>
                    Arquivo:
                </span>
                <span class="metadata-value">${photo.filename}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">
                    <i class="bi bi-hdd me-1"></i>
                    Tamanho:
                </span>
                <span class="metadata-value">${photo.size || 'N/A'}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">
                    <i class="bi bi-aspect-ratio me-1"></i>
                    Dimensões:
                </span>
                <span class="metadata-value">${photo.dimensions || 'N/A'}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">
                    <i class="bi bi-hash me-1"></i>
                    Posição:
                </span>
                <span class="metadata-value">${photo.index}</span>
            </div>
        `;
        
        photoMetadata.innerHTML = metadataHTML;
    }
    
    /**
     * Navigate to previous photo
     */
    function previousPhoto() {
        if (carousel && currentPhotoIndex > 0) {
            carousel.prev();
        }
    }
    
    /**
     * Navigate to next photo
     */
    function nextPhoto() {
        if (carousel && currentPhotoIndex < totalPhotos - 1) {
            carousel.next();
        }
    }
    
    /**
     * Go to specific photo by index
     */
    function goToPhoto(index) {
        if (carousel && index >= 0 && index < totalPhotos) {
            carousel.to(index);
        }
    }
    
    /**
     * Zoom photo by factor
     */
    function zoomPhoto(factor) {
        const activeImg = getActiveImage();
        if (!activeImg) return;
        
        zoomLevel *= factor;
        zoomLevel = Math.max(0.5, Math.min(zoomLevel, 3)); // Limit zoom range
        
        applyImageTransform(activeImg);
        
        // Toggle cursor style
        if (zoomLevel > 1) {
            activeImg.style.cursor = 'grab';
        } else {
            activeImg.style.cursor = 'default';
            imagePosition = { x: 0, y: 0 }; // Reset position when zoomed out
        }
        
        // Update zoom button states
        updateZoomButtonStates();
    }
    
    /**
     * Reset zoom to original size
     */
    function resetZoom() {
        const activeImg = getActiveImage();
        if (!activeImg) return;
        
        zoomLevel = 1;
        imagePosition = { x: 0, y: 0 };
        
        applyImageTransform(activeImg);
        activeImg.style.cursor = 'default';
        
        updateZoomButtonStates();
    }
    
    /**
     * Apply transform to image
     */
    function applyImageTransform(img) {
        img.style.transform = `scale(${zoomLevel}) translate(${imagePosition.x}px, ${imagePosition.y}px)`;
    }
    
    /**
     * Update zoom button states
     */
    function updateZoomButtonStates() {
        const zoomInBtn = document.getElementById('zoomInBtn');
        const zoomOutBtn = document.getElementById('zoomOutBtn');
        const originalSizeBtn = document.getElementById('originalSizeBtn');
        
        if (zoomInBtn) {
            zoomInBtn.disabled = zoomLevel >= 3;
        }
        
        if (zoomOutBtn) {
            zoomOutBtn.disabled = zoomLevel <= 0.5;
        }
        
        if (originalSizeBtn) {
            originalSizeBtn.disabled = zoomLevel === 1 && imagePosition.x === 0 && imagePosition.y === 0;
        }
    }
    
    /**
     * Get currently active image
     */
    function getActiveImage() {
        if (!carouselElement) return null;
        
        const activeItem = carouselElement.querySelector('.carousel-item.active');
        return activeItem ? activeItem.querySelector('img') : null;
    }
    
    /**
     * Initialize image dragging for zoomed photos
     */
    function initializeImageDragging() {
        if (!carouselElement) return;
        
        carouselElement.addEventListener('mousedown', startDrag);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', endDrag);
        
        // Touch events for mobile
        carouselElement.addEventListener('touchstart', startDrag);
        document.addEventListener('touchmove', drag);
        document.addEventListener('touchend', endDrag);
    }
    
    /**
     * Start dragging image
     */
    function startDrag(e) {
        const activeImg = getActiveImage();
        if (!activeImg || zoomLevel <= 1) return;
        
        isDragging = true;
        const event = e.type.includes('touch') ? e.touches[0] : e;
        dragStart.x = event.clientX - imagePosition.x;
        dragStart.y = event.clientY - imagePosition.y;
        
        activeImg.style.cursor = 'grabbing';
        e.preventDefault();
    }
    
    /**
     * Drag image
     */
    function drag(e) {
        const activeImg = getActiveImage();
        if (!isDragging || !activeImg || zoomLevel <= 1) return;
        
        const event = e.type.includes('touch') ? e.touches[0] : e;
        imagePosition.x = event.clientX - dragStart.x;
        imagePosition.y = event.clientY - dragStart.y;
        
        applyImageTransform(activeImg);
        e.preventDefault();
    }
    
    /**
     * End dragging image
     */
    function endDrag() {
        const activeImg = getActiveImage();
        if (isDragging && activeImg) {
            isDragging = false;
            activeImg.style.cursor = zoomLevel > 1 ? 'grab' : 'default';
        }
    }
    
    /**
     * Toggle fullscreen mode
     */
    function toggleFullscreen() {
        if (isFullscreen) {
            exitFullscreen();
        } else {
            enterFullscreen();
        }
    }
    
    /**
     * Enter fullscreen mode
     */
    function enterFullscreen() {
        if (!carouselElement) return;
        
        if (carouselElement.requestFullscreen) {
            carouselElement.requestFullscreen();
        } else if (carouselElement.webkitRequestFullscreen) {
            carouselElement.webkitRequestFullscreen();
        } else if (carouselElement.msRequestFullscreen) {
            carouselElement.msRequestFullscreen();
        }
    }
    
    /**
     * Exit fullscreen mode
     */
    function exitFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
    
    /**
     * Handle fullscreen change
     */
    function handleFullscreenChange() {
        isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
        
        // Update fullscreen button
        const fullPageBtn = document.getElementById('fullPageBtn');
        if (fullPageBtn) {
            const icon = fullPageBtn.querySelector('i');
            if (icon) {
                icon.className = isFullscreen ? 'bi bi-fullscreen-exit' : 'bi bi-arrows-fullscreen';
            }
            fullPageBtn.title = isFullscreen ? 'Sair da Tela Cheia' : 'Tela Cheia';
        }
        
        // Adjust carousel for fullscreen
        if (carouselElement) {
            carouselElement.classList.toggle('fullscreen-mode', isFullscreen);
        }
    }
    
    /**
     * Download current photo
     */
    function downloadCurrentPhoto() {
        if (currentPhotoIndex >= 0 && currentPhotoIndex < photos.length) {
            const photo = photos[currentPhotoIndex];
            if (photo.downloadUrl) {
                // Create temporary link and trigger download
                const link = document.createElement('a');
                link.href = photo.downloadUrl;
                link.download = photo.filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }
    }
    
    /**
     * Handle window resize
     */
    function handleWindowResize() {
        // Reset zoom and position on resize
        resetZoom();
        
        // Update carousel dimensions if needed
        if (carousel) {
            carousel._setCarouselHeight();
        }
    }
    
    /**
     * Show loading state
     */
    function showLoading() {
        const loading = document.getElementById('photoLoading');
        if (loading) {
            loading.classList.remove('d-none');
        }
    }
    
    /**
     * Hide loading state
     */
    function hideLoading() {
        const loading = document.getElementById('photoLoading');
        if (loading) {
            loading.classList.add('d-none');
        }
    }
    
    /**
     * Show error state
     */
    function showError(message) {
        const error = document.getElementById('photoError');
        if (error) {
            const errorMessage = error.querySelector('.error-message');
            if (errorMessage) {
                errorMessage.textContent = message || 'Erro ao carregar foto';
            }
            error.classList.remove('d-none');
        }
    }
    
    /**
     * Hide error state
     */
    function hideError() {
        const error = document.getElementById('photoError');
        if (error) {
            error.classList.add('d-none');
        }
    }
    
    // Listen for fullscreen events
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);
    
    /**
     * Multi-file upload handling (Simplified - delegates to MultiUpload)
     */
    function initializeMultiUpload() {
        // Delegate to the MultiUpload interface from multi_upload.html
        // This avoids conflicts and ensures proper functionality
        console.log('PhotoSeries multi-upload: Delegating to MultiUpload interface');
    }

    /**
     * AJAX photo addition
     */
    function addPhotoToSeries(seriesId, formData) {
        return fetch(`/mediafiles/photo-series/${seriesId}/add-photo/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload page to show new photo
                window.location.reload();
            } else {
                throw new Error(data.error || 'Erro ao adicionar foto');
            }
        })
        .catch(error => {
            console.error('Error adding photo:', error);
            showUploadError(error.message);
        });
    }

    /**
     * AJAX photo removal
     */
    function removePhotoFromSeries(seriesId, photoId) {
        return fetch(`/mediafiles/photo-series/${seriesId}/remove-photo/${photoId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload page to reflect changes
                window.location.reload();
            } else {
                throw new Error(data.error || 'Erro ao remover foto');
            }
        })
        .catch(error => {
            console.error('Error removing photo:', error);
            alert('Erro ao remover foto: ' + error.message);
        });
    }

    /**
     * AJAX photo reordering
     */
    function reorderPhotos(seriesId, photoOrder) {
        return fetch(`/mediafiles/photo-series/${seriesId}/reorder/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ photo_order: photoOrder })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Photos reordered successfully');
                return data;
            } else {
                throw new Error(data.error || 'Erro ao reordenar fotos');
            }
        })
        .catch(error => {
            console.error('Error reordering photos:', error);
            alert('Erro ao reordenar fotos: ' + error.message);
        });
    }

    /**
     * Get CSRF token
     */
    function getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    /**
     * Handle breadcrumb navigation
     */
    function initializeBreadcrumbNavigation() {
        const breadcrumbLinks = document.querySelectorAll('.breadcrumb-link');
        breadcrumbLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // Add loading state to clicked breadcrumb
                this.classList.add('loading');
            });
        });
    }

    /**
     * Return to timeline functionality
     */
    function returnToTimeline() {
        const timelineUrl = document.querySelector('[data-timeline-url]');
        if (timelineUrl) {
            window.location.href = timelineUrl.dataset.timelineUrl;
        } else {
            // Fallback: go back in history
            window.history.back();
        }
    }

    /**
     * Initialize PhotoSeries functionality in timeline cards
     */
    function initializeTimelinePhotoSeries() {
        // Handle PhotoSeries thumbnail click to open lightbox or detail view
        const photoSeriesThumbnails = document.querySelectorAll('.photoseries-thumbnail-wrapper');
        
        photoSeriesThumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', function(e) {
                // Prevent click if it's on an action button
                if (e.target.closest('.btn') || e.target.closest('.dropdown')) {
                    return;
                }
                
                // Check if this thumbnail should trigger lightbox
                const trigger = this.getAttribute('data-trigger');
                const galleryId = this.getAttribute('data-gallery-id');
                
                if (trigger === 'lightbox' && galleryId && window.PhotoLightbox && window.PhotoLightbox.open) {
                    // Open lightbox
                    e.preventDefault();
                    console.log('PhotoSeries: Opening lightbox for gallery:', galleryId);
                    try {
                        PhotoLightbox.open(0, galleryId);
                        return; // Exit early if lightbox opened successfully
                    } catch (error) {
                        console.warn('PhotoSeries: Failed to open PhotoLightbox:', error);
                        // Fall through to detail page navigation
                    }
                } else {
                    console.warn('PhotoSeries: Lightbox not available or missing data:', {
                        trigger: trigger,
                        galleryId: galleryId,
                        hasPhotoLightbox: !!(window.PhotoLightbox && window.PhotoLightbox.open)
                    });
                }
                
                // Fallback to detail page navigation
                const timelineCard = this.closest('.timeline-card');
                if (timelineCard) {
                    const eventId = timelineCard.getAttribute('aria-labelledby').replace('event-', '').replace('-title', '');
                    
                    // Navigate to PhotoSeries detail view
                    const detailUrl = `/mediafiles/photo-series/${eventId}/`;
                    window.location.href = detailUrl;
                }
            });
        });
        
        // Handle keyboard navigation for PhotoSeries cards
        photoSeriesThumbnails.forEach(thumbnail => {
            if (!thumbnail.hasAttribute('tabindex')) {
                thumbnail.setAttribute('tabindex', '0');
            }
            if (!thumbnail.hasAttribute('role')) {
                thumbnail.setAttribute('role', 'button');
            }
            if (!thumbnail.hasAttribute('aria-label')) {
                thumbnail.setAttribute('aria-label', 'Visualizar série de fotos');
            }
            
            thumbnail.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
    }

    // Public API
    return {
        init: init,
        previousPhoto: previousPhoto,
        nextPhoto: nextPhoto,
        goToPhoto: goToPhoto,
        zoomPhoto: zoomPhoto,
        resetZoom: resetZoom,
        toggleFullscreen: toggleFullscreen,
        downloadCurrentPhoto: downloadCurrentPhoto,
        initializeMultiUpload: initializeMultiUpload,
        initializeBreadcrumbNavigation: initializeBreadcrumbNavigation,
        addPhotoToSeries: addPhotoToSeries,
        removePhotoFromSeries: removePhotoFromSeries,
        reorderPhotos: reorderPhotos,
        returnToTimeline: returnToTimeline,
        initializeTimelinePhotoSeries: initializeTimelinePhotoSeries,
        getCurrentIndex: () => currentPhotoIndex,
        getTotalPhotos: () => totalPhotos,
        getPhotos: () => photos
    };
})();

