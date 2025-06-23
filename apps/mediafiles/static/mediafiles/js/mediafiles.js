/**
 * MediaFiles JavaScript
 * 
 * Provides interactive functionality for the EquipeMed MediaFiles app
 * Handles file uploads, previews, validation, and user interactions
 */

// MediaFiles namespace
window.MediaFiles = (function() {
    'use strict';

    // Configuration
    const config = {
        maxImageSize: 5 * 1024 * 1024, // 5MB
        maxVideoSize: 50 * 1024 * 1024, // 50MB
        allowedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
        allowedVideoTypes: ['video/mp4', 'video/webm', 'video/quicktime'],
        allowedImageExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
        allowedVideoExtensions: ['.mp4', '.webm', '.mov']
    };

    // Utility functions
    const utils = {
        /**
         * Format file size in human readable format
         */
        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        /**
         * Get file extension from filename
         */
        getFileExtension: function(filename) {
            return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
        },

        /**
         * Validate file type
         */
        validateFileType: function(file, allowedTypes) {
            return allowedTypes.includes(file.type);
        },

        /**
         * Validate file size
         */
        validateFileSize: function(file, maxSize) {
            return file.size <= maxSize;
        },

        /**
         * Show toast notification
         */
        showToast: function(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            toast.innerHTML = `
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.body.appendChild(toast);
            
            // Auto-remove after 4 seconds
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 4000);
        },

        /**
         * Debounce function
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };

    // File upload handler
    const fileUpload = {
        /**
         * Initialize file upload functionality
         */
        init: function() {
            this.setupDragAndDrop();
            this.setupFileInputs();
        },

        /**
         * Setup drag and drop functionality
         */
        setupDragAndDrop: function() {
            const uploadAreas = document.querySelectorAll('.media-upload-area');
            
            uploadAreas.forEach(area => {
                area.addEventListener('dragover', this.handleDragOver.bind(this));
                area.addEventListener('dragleave', this.handleDragLeave.bind(this));
                area.addEventListener('drop', this.handleDrop.bind(this));
            });
        },

        /**
         * Setup file input change handlers
         */
        setupFileInputs: function() {
            const fileInputs = document.querySelectorAll('input[type="file"]');
            
            fileInputs.forEach(input => {
                input.addEventListener('change', this.handleFileSelect.bind(this));
            });
        },

        /**
         * Handle drag over event
         */
        handleDragOver: function(e) {
            e.preventDefault();
            e.currentTarget.classList.add('dragover');
        },

        /**
         * Handle drag leave event
         */
        handleDragLeave: function(e) {
            e.preventDefault();
            e.currentTarget.classList.remove('dragover');
        },

        /**
         * Handle drop event
         */
        handleDrop: function(e) {
            e.preventDefault();
            e.currentTarget.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = e.currentTarget.querySelector('input[type="file"]');
                if (fileInput) {
                    fileInput.files = files;
                    this.handleFileSelect({ target: fileInput });
                }
            }
        },

        /**
         * Handle file selection
         */
        handleFileSelect: function(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Validate file
            if (!this.validateFile(file)) {
                return;
            }

            // Show preview
            this.showPreview(file, e.target);
        },

        /**
         * Validate selected file
         */
        validateFile: function(file) {
            // Check file type
            const isImage = utils.validateFileType(file, config.allowedImageTypes);
            const isVideo = utils.validateFileType(file, config.allowedVideoTypes);
            
            if (!isImage && !isVideo) {
                utils.showToast('Tipo de arquivo não permitido.', 'error');
                return false;
            }

            // Check file size
            const maxSize = isImage ? config.maxImageSize : config.maxVideoSize;
            if (!utils.validateFileSize(file, maxSize)) {
                const maxSizeMB = maxSize / (1024 * 1024);
                utils.showToast(`Arquivo muito grande. Máximo: ${maxSizeMB}MB`, 'error');
                return false;
            }

            return true;
        },

        /**
         * Show file preview
         */
        showPreview: function(file, input) {
            const previewContainer = document.getElementById('imagePreview') || 
                                   document.getElementById('videoPreview');
            
            if (!previewContainer) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                const previewElement = previewContainer.querySelector('img, video');
                if (previewElement) {
                    previewElement.src = e.target.result;
                }
                
                // Update metadata
                fileUpload.updateMetadata(file);
                
                // Show preview container
                previewContainer.style.display = 'block';
                
                // Hide upload area
                const uploadArea = input.closest('.media-upload-area');
                if (uploadArea) {
                    uploadArea.style.display = 'none';
                }
            };
            reader.readAsDataURL(file);
        },

        /**
         * Update file metadata display
         */
        updateMetadata: function(file) {
            const elements = {
                fileName: document.getElementById('fileName'),
                fileSize: document.getElementById('fileSize'),
                fileType: document.getElementById('fileType')
            };

            if (elements.fileName) elements.fileName.textContent = file.name;
            if (elements.fileSize) elements.fileSize.textContent = utils.formatFileSize(file.size);
            if (elements.fileType) elements.fileType.textContent = file.type;
        }
    };

    // Photo modal functionality
    const photoModal = {
        /**
         * Initialize photo modal functionality
         */
        init: function() {
            this.setupPhotoModal();
            this.setupZoomControls();
            this.setupKeyboardNavigation();
        },

        /**
         * Setup photo modal event listeners
         */
        setupPhotoModal: function() {
            const modal = document.getElementById('photoModal');
            if (!modal) {
                return;
            }

            modal.addEventListener('show.bs.modal', this.handleModalShow.bind(this));
            modal.addEventListener('hidden.bs.modal', this.handleModalHidden.bind(this));
        },

        /**
         * Setup zoom controls
         */
        setupZoomControls: function() {
            const zoomInBtn = document.getElementById('photoZoomIn');
            const zoomOutBtn = document.getElementById('photoZoomOut');
            const zoomResetBtn = document.getElementById('photoZoomReset');
            const fullscreenBtn = document.getElementById('photoFullscreenToggle');
            const modalImage = document.getElementById('photoModalImage');

            if (zoomInBtn) zoomInBtn.addEventListener('click', () => this.zoomIn());
            if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => this.zoomOut());
            if (zoomResetBtn) zoomResetBtn.addEventListener('click', () => this.resetZoom());
            if (fullscreenBtn) fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
            if (modalImage) {
                modalImage.addEventListener('click', (e) => this.handleImageClick(e));
                // Setup panning event handlers
                modalImage.addEventListener('mousedown', (e) => this.startPan(e));
                modalImage.addEventListener('mousemove', (e) => this.updatePan(e));
                modalImage.addEventListener('mouseup', () => this.endPan());
                modalImage.addEventListener('mouseleave', () => this.endPan());
                
                // Touch event handlers for mobile
                modalImage.addEventListener('touchstart', (e) => this.startPan(e));
                modalImage.addEventListener('touchmove', (e) => this.updatePan(e));
                modalImage.addEventListener('touchend', () => this.endPan());
            }
        },

        /**
         * Setup keyboard navigation
         */
        setupKeyboardNavigation: function() {
            const modal = document.getElementById('photoModal');
            if (!modal) return;

            modal.addEventListener('keydown', (e) => {
                switch(e.key) {
                    case 'Escape':
                        bootstrap.Modal.getInstance(modal).hide();
                        break;
                    case '+':
                    case '=':
                        this.zoomIn();
                        break;
                    case '-':
                        this.zoomOut();
                        break;
                    case '0':
                        this.resetZoom();
                        break;
                    case 'f':
                    case 'F':
                        e.preventDefault();
                        this.toggleFullscreen();
                        break;
                }
            });
        },

        /**
         * Handle modal show event
         */
        handleModalShow: function(event) {
            const trigger = event.relatedTarget;
            if (!trigger) {
                return;
            }

            // Reset modal state
            this.resetModalState();

            // Get photo data from trigger element
            const photoData = {
                id: trigger.dataset.photoId,
                url: trigger.dataset.photoUrl,
                title: trigger.dataset.photoTitle || 'Foto',
                filename: trigger.dataset.photoFilename || '-',
                size: trigger.dataset.photoSize || '-',
                dimensions: trigger.dataset.photoDimensions || '-',
                created: trigger.dataset.photoCreated || '-',
                author: trigger.dataset.photoAuthor || '-'
            };

            // Update modal content
            this.updateModalContent(photoData);

            // Load the image
            this.loadPhotoImage(photoData.url);
        },

        /**
         * Handle modal hidden event
         */
        handleModalHidden: function() {
            this.resetModalState();
        },

        /**
         * Reset modal state
         */
        resetModalState: function() {
            this.currentZoom = 1;
            this.isFullscreen = false;
            this.isPanning = false;
            this.panX = 0;
            this.panY = 0;
            
            const modal = document.getElementById('photoModal');
            const modalDialog = modal?.querySelector('.modal-dialog');
            const container = document.getElementById('photoModalContainer');
            const loading = document.getElementById('photoModalLoading');
            const error = document.getElementById('photoModalError');
            const image = document.getElementById('photoModalImage');
            const fullscreenBtn = document.getElementById('photoFullscreenToggle');
            const fullscreenIcon = fullscreenBtn?.querySelector('i');

            if (container) container.classList.add('d-none');
            if (loading) loading.classList.remove('d-none');
            if (error) error.classList.add('d-none');
            if (image) {
                image.style.transform = 'scale(1)';
                image.style.cursor = 'zoom-in';
                image.style.maxHeight = '70vh';
                image.style.maxWidth = '';
                image.style.objectFit = '';
            }
            
            // Reset fullscreen state
            if (modalDialog) {
                modalDialog.classList.remove('modal-fullscreen');
                modalDialog.classList.add('modal-xl', 'modal-dialog-centered');
            }
            
            // Reset fullscreen button
            if (fullscreenIcon) {
                fullscreenIcon.className = 'bi bi-arrows-fullscreen';
            }
            if (fullscreenBtn) {
                fullscreenBtn.title = 'Tela cheia';
                const hiddenSpan = fullscreenBtn.querySelector('.visually-hidden');
                if (hiddenSpan) hiddenSpan.textContent = 'Tela cheia';
            }
        },

        /**
         * Update modal content with photo data
         */
        updateModalContent: function(photoData) {
            const elements = {
                title: document.getElementById('photoModalTitle'),
                filename: document.getElementById('photoModalFilename'),
                dimensions: document.getElementById('photoModalDimensions'),
                size: document.getElementById('photoModalSize'),
                created: document.getElementById('photoModalCreated'),
                author: document.getElementById('photoModalAuthor'),
                downloadBtn: document.getElementById('photoDownloadBtn')
            };

            if (elements.title) elements.title.textContent = photoData.title;
            if (elements.filename) elements.filename.textContent = photoData.filename;
            if (elements.dimensions) elements.dimensions.textContent = photoData.dimensions;
            if (elements.size) elements.size.textContent = photoData.size;
            if (elements.created) elements.created.textContent = photoData.created;
            if (elements.author) elements.author.textContent = photoData.author;

            // Update download link
            if (elements.downloadBtn) {
                elements.downloadBtn.href = photoData.url + '?download=1';
                elements.downloadBtn.download = photoData.filename;
            }
        },

        /**
         * Load photo image
         */
        loadPhotoImage: function(imageUrl) {
            const img = new Image();
            const modalImage = document.getElementById('photoModalImage');
            const loading = document.getElementById('photoModalLoading');
            const container = document.getElementById('photoModalContainer');
            const error = document.getElementById('photoModalError');

            img.onload = () => {
                if (modalImage) {
                    modalImage.src = imageUrl;
                    modalImage.alt = document.getElementById('photoModalFilename')?.textContent || 'Photo';
                }
                if (loading) loading.classList.add('d-none');
                if (container) container.classList.remove('d-none');
            };

            img.onerror = () => {
                if (loading) loading.classList.add('d-none');
                if (error) error.classList.remove('d-none');
            };

            img.src = imageUrl;
        },

        // Zoom functionality
        currentZoom: 1,
        zoomStep: 0.25,
        maxZoom: 3,
        minZoom: 0.5,
        
        // Fullscreen functionality
        isFullscreen: false,
        
        // Panning functionality
        isPanning: false,
        panStartX: 0,
        panStartY: 0,
        panX: 0,
        panY: 0,

        /**
         * Zoom in
         */
        zoomIn: function() {
            if (this.currentZoom < this.maxZoom) {
                this.currentZoom += this.zoomStep;
                this.updateImageZoom();
            }
        },

        /**
         * Zoom out
         */
        zoomOut: function() {
            if (this.currentZoom > this.minZoom) {
                this.currentZoom -= this.zoomStep;
                this.updateImageZoom();
            }
        },

        /**
         * Reset zoom
         */
        resetZoom: function() {
            this.currentZoom = 1;
            this.panX = 0;
            this.panY = 0;
            this.updateImageZoom();
        },

        /**
         * Toggle zoom (click to zoom)
         */
        toggleZoom: function() {
            if (this.currentZoom < this.maxZoom) {
                this.currentZoom += this.zoomStep;
            } else {
                this.currentZoom = 1;
            }
            this.updateImageZoom();
        },

        /**
         * Update image zoom and pan
         */
        updateImageZoom: function() {
            const image = document.getElementById('photoModalImage');
            if (image) {
                image.style.transform = `scale(${this.currentZoom}) translate(${this.panX}px, ${this.panY}px)`;
                
                // Update cursor based on zoom level and pan state
                if (this.isPanning) {
                    image.style.cursor = 'grabbing';
                } else if (this.currentZoom > 1) {
                    image.style.cursor = 'grab';
                } else {
                    image.style.cursor = this.currentZoom >= this.maxZoom ? 'zoom-out' : 'zoom-in';
                }
            }
        },

        /**
         * Toggle fullscreen mode
         */
        toggleFullscreen: function() {
            const modal = document.getElementById('photoModal');
            const modalDialog = modal?.querySelector('.modal-dialog');
            const modalImage = document.getElementById('photoModalImage');
            const fullscreenBtn = document.getElementById('photoFullscreenToggle');
            const fullscreenIcon = fullscreenBtn?.querySelector('i');
            
            if (!modal || !modalDialog) return;
            
            this.isFullscreen = !this.isFullscreen;
            
            if (this.isFullscreen) {
                // Switch to fullscreen
                modalDialog.classList.remove('modal-xl', 'modal-dialog-centered');
                modalDialog.classList.add('modal-fullscreen');
                
                if (modalImage) {
                    modalImage.style.maxHeight = '100vh';
                    modalImage.style.maxWidth = '100vw';
                    modalImage.style.objectFit = 'contain';
                }
                
                // Update button icon
                if (fullscreenIcon) {
                    fullscreenIcon.className = 'bi bi-fullscreen-exit';
                }
                if (fullscreenBtn) {
                    fullscreenBtn.title = 'Sair da tela cheia';
                    fullscreenBtn.querySelector('.visually-hidden').textContent = 'Sair da tela cheia';
                }
            } else {
                // Switch back to normal
                modalDialog.classList.remove('modal-fullscreen');
                modalDialog.classList.add('modal-xl', 'modal-dialog-centered');
                
                if (modalImage) {
                    modalImage.style.maxHeight = '70vh';
                    modalImage.style.maxWidth = '';
                    modalImage.style.objectFit = '';
                }
                
                // Update button icon
                if (fullscreenIcon) {
                    fullscreenIcon.className = 'bi bi-arrows-fullscreen';
                }
                if (fullscreenBtn) {
                    fullscreenBtn.title = 'Tela cheia';
                    fullscreenBtn.querySelector('.visually-hidden').textContent = 'Tela cheia';
                }
            }
        },

        /**
         * Handle image click (distinguish between click and pan)
         */
        handleImageClick: function(e) {
            // Only toggle zoom if we weren't panning
            if (!this.isPanning && Math.abs(this.panStartX - e.clientX) < 5 && Math.abs(this.panStartY - e.clientY) < 5) {
                this.toggleZoom();
            }
        },

        /**
         * Start panning
         */
        startPan: function(e) {
            // Only allow panning when zoomed
            if (this.currentZoom <= 1) return;
            
            e.preventDefault();
            this.isPanning = true;
            
            // Get initial position
            const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
            const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;
            
            this.panStartX = clientX - this.panX;
            this.panStartY = clientY - this.panY;
            
            this.updateImageZoom();
        },

        /**
         * Update panning
         */
        updatePan: function(e) {
            if (!this.isPanning) return;
            
            e.preventDefault();
            
            // Get current position
            const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
            const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
            
            // Calculate new pan position
            this.panX = clientX - this.panStartX;
            this.panY = clientY - this.panStartY;
            
            this.updateImageZoom();
        },

        /**
         * End panning
         */
        endPan: function() {
            this.isPanning = false;
            this.updateImageZoom();
        }
    };

    // Image viewer functionality (legacy support)
    const imageViewer = {
        /**
         * Initialize image viewer
         */
        init: function() {
            this.setupImageModals();
            this.setupZoomFunctionality();
        },

        /**
         * Setup image modal triggers
         */
        setupImageModals: function() {
            const imageLinks = document.querySelectorAll('[data-bs-toggle="modal"][data-bs-target*="imageModal"]');

            imageLinks.forEach(link => {
                link.addEventListener('click', this.handleImageModalOpen.bind(this));
            });
        },

        /**
         * Setup zoom functionality
         */
        setupZoomFunctionality: function() {
            const zoomableImages = document.querySelectorAll('.zoomable-image');

            zoomableImages.forEach(img => {
                img.addEventListener('click', this.toggleZoom.bind(this));
            });
        },

        /**
         * Handle image modal open
         */
        handleImageModalOpen: function(e) {
            const imageSrc = e.currentTarget.dataset.imageSrc;
            const modal = document.querySelector(e.currentTarget.dataset.bsTarget);

            if (modal && imageSrc) {
                const modalImage = modal.querySelector('.modal-body img');
                if (modalImage) {
                    modalImage.src = imageSrc;
                }
            }
        },

        /**
         * Toggle image zoom
         */
        toggleZoom: function(e) {
            const img = e.currentTarget;
            img.classList.toggle('zoomed');
        }
    };

    // Shared configuration accessible to other modules
    const sharedConfig = {
        maxImageSize: config.maxImageSize,
        maxVideoSize: config.maxVideoSize,
        allowedImageTypes: config.allowedImageTypes,
        allowedVideoTypes: config.allowedVideoTypes,
        allowedImageExtensions: config.allowedImageExtensions,
        allowedVideoExtensions: config.allowedVideoExtensions
    };

    // Public API
    return {
        /**
         * Initialize all MediaFiles functionality
         */
        init: function() {
            fileUpload.init();
            imageViewer.init();
            photoModal.init();

            // Initialize tooltips
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl =>
                new bootstrap.Tooltip(tooltipTriggerEl)
            );
        },

        // Expose utilities for shared use
        utils: utils,
        config: sharedConfig,
        fileUpload: fileUpload,
        imageViewer: imageViewer,
        photoModal: photoModal
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (typeof bootstrap !== 'undefined') {
        MediaFiles.init();
    }
});
