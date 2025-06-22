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

    // Image viewer functionality
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

    // Public API
    return {
        /**
         * Initialize all MediaFiles functionality
         */
        init: function() {
            fileUpload.init();
            imageViewer.init();
            
            // Initialize tooltips
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => 
                new bootstrap.Tooltip(tooltipTriggerEl)
            );
        },

        // Expose utilities
        utils: utils,
        fileUpload: fileUpload,
        imageViewer: imageViewer
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (typeof bootstrap !== 'undefined') {
        MediaFiles.init();
    }
});
