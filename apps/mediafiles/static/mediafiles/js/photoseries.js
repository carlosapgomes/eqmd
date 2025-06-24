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
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', downloadCurrentPhoto);
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
        const direction = event.direction;
        const relatedTarget = event.relatedTarget;
        
        // Reset zoom when changing photos
        resetZoom();
        
        // Update current index based on direction
        if (direction === 'left') {
            currentPhotoIndex = Math.min(currentPhotoIndex + 1, totalPhotos - 1);
        } else {
            currentPhotoIndex = Math.max(currentPhotoIndex - 1, 0);
        }
        
        // Update photo info
        updatePhotoInfo(currentPhotoIndex);
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
        }
    }
    
    /**
     * Update photo information panel
     */
    function updatePhotoInfo(index) {
        if (index < 0 || index >= photos.length) return;
        
        const photo = photos[index];
        
        // Update counter
        if (photoCounter) {
            photoCounter.textContent = `${index + 1} de ${totalPhotos}`;
        }
        
        // Update metadata
        if (photoMetadata && photo) {
            updatePhotoMetadata(photo);
        }
        
        // Update download link
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn && photo.downloadUrl) {
            downloadBtn.href = photo.downloadUrl;
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
     * Multi-file upload handling
     */
    function initializeMultiUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('id_images');
        const previewContainer = document.getElementById('uploadPreview');

        if (!uploadArea || !fileInput) return;

        // Drag and drop functionality
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleFileDrop);

        // File input change
        fileInput.addEventListener('change', handleFileSelect);

        // Click to select files
        uploadArea.addEventListener('click', () => fileInput.click());
    }

    /**
     * Handle drag over event
     */
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.add('drag-over');
    }

    /**
     * Handle drag leave event
     */
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('drag-over');
    }

    /**
     * Handle file drop event
     */
    function handleFileDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        handleFiles(files);
    }

    /**
     * Handle file selection
     */
    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }

    /**
     * Process selected files
     */
    function handleFiles(files) {
        const previewContainer = document.getElementById('uploadPreview');
        if (!previewContainer) return;

        // Clear existing previews
        previewContainer.innerHTML = '';

        // Validate and preview each file
        Array.from(files).forEach((file, index) => {
            if (validateFile(file)) {
                createFilePreview(file, index, previewContainer);
            }
        });

        // Show preview container
        previewContainer.classList.remove('d-none');

        // Update upload area state
        updateUploadAreaState(files.length);
    }

    /**
     * Validate individual file
     */
    function validateFile(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!allowedTypes.includes(file.type)) {
            showUploadError(`Tipo de arquivo não permitido: ${file.name}`);
            return false;
        }

        if (file.size > maxSize) {
            showUploadError(`Arquivo muito grande: ${file.name}`);
            return false;
        }

        return true;
    }

    /**
     * Create file preview
     */
    function createFilePreview(file, index, container) {
        const previewDiv = document.createElement('div');
        previewDiv.className = 'upload-preview-item';
        previewDiv.dataset.index = index;

        const img = document.createElement('img');
        img.className = 'preview-thumbnail';

        const reader = new FileReader();
        reader.onload = function(e) {
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);

        const info = document.createElement('div');
        info.className = 'preview-info';
        info.innerHTML = `
            <div class="preview-filename">${file.name}</div>
            <div class="preview-size">${formatFileSize(file.size)}</div>
            <div class="preview-progress">
                <div class="progress">
                    <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-sm btn-outline-danger preview-remove';
        removeBtn.innerHTML = '<i class="bi bi-x"></i>';
        removeBtn.addEventListener('click', () => removeFilePreview(previewDiv, index));

        previewDiv.appendChild(img);
        previewDiv.appendChild(info);
        previewDiv.appendChild(removeBtn);

        container.appendChild(previewDiv);
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
        getCurrentIndex: () => currentPhotoIndex,
        getTotalPhotos: () => totalPhotos,
        getPhotos: () => photos
    };
})();

    /**
     * Remove file preview
     */
    function removeFilePreview(previewDiv, index) {
        const fileInput = document.getElementById('id_images');
        if (fileInput) {
            // Create new FileList without the removed file
            const dt = new DataTransfer();
            Array.from(fileInput.files).forEach((file, i) => {
                if (i !== index) {
                    dt.items.add(file);
                }
            });
            fileInput.files = dt.files;
        }

        previewDiv.remove();

        // Update indices of remaining previews
        const remainingPreviews = document.querySelectorAll('.upload-preview-item');
        remainingPreviews.forEach((preview, newIndex) => {
            preview.dataset.index = newIndex;
        });

        // Hide preview container if no files
        const previewContainer = document.getElementById('uploadPreview');
        if (previewContainer && remainingPreviews.length === 0) {
            previewContainer.classList.add('d-none');
        }
    }

    /**
     * Format file size for display
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Update upload area state
     */
    function updateUploadAreaState(fileCount) {
        const uploadArea = document.getElementById('uploadArea');
        if (!uploadArea) return;

        const content = uploadArea.querySelector('.upload-content');
        if (content) {
            if (fileCount > 0) {
                content.innerHTML = `
                    <i class="bi bi-check-circle display-4 text-success mb-3"></i>
                    <h5 class="text-success">${fileCount} arquivo(s) selecionado(s)</h5>
                    <p class="text-muted">Clique para selecionar mais arquivos</p>
                `;
            } else {
                content.innerHTML = `
                    <i class="bi bi-cloud-upload display-4 text-medical-gray mb-3"></i>
                    <h5 class="text-medical-primary">Clique para selecionar ou arraste as imagens aqui</h5>
                    <p class="text-muted">Formatos aceitos: JPG, PNG, GIF, WebP (máx. 10MB cada)</p>
                `;
            }
        }
    }

    /**
     * Show upload error
     */
    function showUploadError(message) {
        // Create or update error alert
        let errorAlert = document.getElementById('uploadError');
        if (!errorAlert) {
            errorAlert = document.createElement('div');
            errorAlert.id = 'uploadError';
            errorAlert.className = 'alert alert-danger alert-dismissible fade show mt-3';

            const uploadArea = document.getElementById('uploadArea');
            if (uploadArea) {
                uploadArea.parentNode.insertBefore(errorAlert, uploadArea.nextSibling);
            }
        }

        errorAlert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorAlert) {
                errorAlert.remove();
            }
        }, 5000);
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

})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('photoSeriesData')) {
        PhotoSeries.init();
    }

    // Initialize multi-upload if on form page
    if (document.getElementById('uploadArea')) {
        PhotoSeries.initializeMultiUpload();
    }

    // Initialize breadcrumb navigation
    PhotoSeries.initializeBreadcrumbNavigation();
});