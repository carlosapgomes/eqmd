/**
 * Photo-specific JavaScript for EquipeMed MediaFiles
 * 
 * Handles photo upload, preview, validation, and modal interactions
 * Implements Step 3.6 from the media implementation plan
 */

// Photo namespace
window.Photo = (function() {
    'use strict';

    // Photo-specific configuration (extends MediaFiles config)
    const config = {
        maxImageWidth: 4000,
        maxImageHeight: 4000,
        thumbnailSize: 150,
        previewMaxWidth: 800,
        previewMaxHeight: 600
    };

    // Use shared utilities from MediaFiles
    const utils = window.MediaFiles ? window.MediaFiles.utils : {
        formatFileSize: function(bytes) {
            console.warn('MediaFiles not loaded, using fallback formatFileSize');
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },
        getFileExtension: function(filename) {
            console.warn('MediaFiles not loaded, using fallback getFileExtension');
            return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
        },
        showToast: function(message, type = 'info') {
            console.warn('MediaFiles not loaded, using fallback showToast');
            alert(message);
        }
    };

    // Get shared config from MediaFiles
    const sharedConfig = window.MediaFiles ? window.MediaFiles.config : {
        maxImageSize: 5 * 1024 * 1024,
        allowedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
        allowedImageExtensions: ['.jpg', '.jpeg', '.png', '.webp']
    };

    // Photo upload handler
    const photoUpload = {
        /**
         * Initialize photo upload functionality
         */
        init: function() {
            this.setupDragAndDrop();
            this.setupFileInputs();
            this.setupPreviewControls();
        },

        /**
         * Setup drag and drop functionality
         */
        setupDragAndDrop: function() {
            const uploadAreas = document.querySelectorAll('.photo-upload-form');
            
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
            const fileInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
            
            fileInputs.forEach(input => {
                input.addEventListener('change', this.handleFileSelect.bind(this));
            });

            // Setup click handler for upload area
            const uploadArea = document.getElementById('uploadArea');
            if (uploadArea) {
                uploadArea.addEventListener('click', function() {
                    const fileInput = uploadArea.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.click();
                    }
                });
            }
        },

        /**
         * Setup preview controls
         */
        setupPreviewControls: function() {
            const removeButtons = document.querySelectorAll('.photo-preview-remove');
            const changeButtons = document.querySelectorAll('.photo-preview-change');

            removeButtons.forEach(btn => {
                btn.addEventListener('click', this.removePreview.bind(this));
            });

            changeButtons.forEach(btn => {
                btn.addEventListener('click', this.changePhoto.bind(this));
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
            if (!this.validatePhoto(file)) {
                e.target.value = ''; // Clear the input
                return;
            }

            // Show upload progress
            this.showUploadProgress();

            // Process and show preview
            this.processPhoto(file, e.target);
        },

        /**
         * Validate photo file
         */
        validatePhoto: function(file) {
            // Check file type
            if (!sharedConfig.allowedImageTypes.includes(file.type)) {
                utils.showToast('Tipo de arquivo não permitido. Use JPG, PNG ou WebP.', 'danger');
                return false;
            }

            // Check file extension
            const extension = '.' + utils.getFileExtension(file.name);
            if (!sharedConfig.allowedImageExtensions.includes(extension)) {
                utils.showToast('Extensão de arquivo não permitida.', 'danger');
                return false;
            }

            // Check file size
            if (file.size > sharedConfig.maxImageSize) {
                const maxSizeMB = sharedConfig.maxImageSize / (1024 * 1024);
                utils.showToast(`Arquivo muito grande. Máximo: ${maxSizeMB}MB`, 'danger');
                return false;
            }

            return true;
        },

        /**
         * Process photo file
         */
        processPhoto: function(file, input) {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const img = new Image();
                
                img.onload = () => {
                    // Validate image dimensions
                    if (img.width > config.maxImageWidth || img.height > config.maxImageHeight) {
                        utils.showToast(`Imagem muito grande. Máximo: ${config.maxImageWidth}x${config.maxImageHeight}px`, 'danger');
                        input.value = '';
                        this.hideUploadProgress();
                        return;
                    }

                    // Show preview
                    this.showPhotoPreview(e.target.result, file, img.width, img.height);
                    
                    // Hide upload progress
                    this.hideUploadProgress();
                    
                    // Show success message
                    utils.showToast('Foto carregada com sucesso!', 'success');
                };

                img.onerror = () => {
                    utils.showToast('Erro ao carregar a imagem.', 'danger');
                    input.value = '';
                    this.hideUploadProgress();
                };

                img.src = e.target.result;
            };

            reader.onerror = () => {
                utils.showToast('Erro ao ler o arquivo.', 'danger');
                input.value = '';
                this.hideUploadProgress();
            };

            reader.readAsDataURL(file);
        },

        /**
         * Show photo preview
         */
        showPhotoPreview: function(imageSrc, file, width, height) {
            const previewContainer = document.getElementById('photoPreview') || document.getElementById('imagePreview');
            const uploadForm = document.querySelector('.photo-upload-form') || document.getElementById('uploadArea');
            
            if (!previewContainer) return;

            // Update preview image - try multiple selectors for compatibility
            const previewImage = previewContainer.querySelector('.photo-preview-image') || 
                                 previewContainer.querySelector('#previewImage') ||
                                 previewContainer.querySelector('img');
            if (previewImage) {
                previewImage.src = imageSrc;
                previewImage.alt = file.name;
            }

            // Update metadata
            this.updatePhotoMetadata(file, width, height);

            // Show preview, hide upload form
            previewContainer.style.display = 'block';
            if (uploadForm) {
                uploadForm.style.display = 'none';
            }
        },

        /**
         * Update photo metadata display
         */
        updatePhotoMetadata: function(file, width, height) {
            const elements = {
                fileName: document.getElementById('photoFileName') || document.getElementById('fileName'),
                fileSize: document.getElementById('photoFileSize') || document.getElementById('fileSize'),
                dimensions: document.getElementById('photoDimensions') || document.getElementById('dimensions'),
                fileType: document.getElementById('photoFileType') || document.getElementById('fileType')
            };

            if (elements.fileName) elements.fileName.textContent = file.name;
            if (elements.fileSize) elements.fileSize.textContent = utils.formatFileSize(file.size);
            if (elements.dimensions) elements.dimensions.textContent = `${width}x${height}px`;
            if (elements.fileType) elements.fileType.textContent = file.type;
        },

        /**
         * Remove photo preview
         */
        removePreview: function(e) {
            e.preventDefault();
            
            const previewContainer = document.getElementById('photoPreview') || document.getElementById('imagePreview');
            const uploadForm = document.querySelector('.photo-upload-form') || document.getElementById('uploadArea');
            const fileInput = document.querySelector('input[type="file"][accept*="image"]');

            // Clear file input
            if (fileInput) {
                fileInput.value = '';
            }

            // Hide preview, show upload form
            if (previewContainer) {
                previewContainer.style.display = 'none';
            }
            if (uploadForm) {
                uploadForm.style.display = 'block';
            }

            // Clear any error messages
            const errors = document.querySelectorAll('.media-error');
            errors.forEach(error => error.remove());
        },

        /**
         * Change photo (trigger file input)
         */
        changePhoto: function(e) {
            e.preventDefault();
            
            const fileInput = document.querySelector('input[type="file"][accept*="image"]');
            if (fileInput) {
                fileInput.click();
            }
        },

        /**
         * Show upload progress
         */
        showUploadProgress: function() {
            const progressContainer = document.getElementById('photoUploadProgress');
            if (progressContainer) {
                progressContainer.style.display = 'block';
                
                // Simulate progress
                const progressBar = progressContainer.querySelector('.photo-progress-fill');
                const progressText = progressContainer.querySelector('.photo-progress-text');
                
                if (progressBar && progressText) {
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += Math.random() * 30;
                        if (progress >= 100) {
                            progress = 100;
                            clearInterval(interval);
                        }
                        
                        progressBar.style.width = progress + '%';
                        progressText.textContent = `Processando... ${Math.round(progress)}%`;
                    }, 100);
                }
            }
        },

        /**
         * Hide upload progress
         */
        hideUploadProgress: function() {
            const progressContainer = document.getElementById('photoUploadProgress');
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        }
    };

    // Public API
    return {
        /**
         * Initialize all photo functionality
         */
        init: function() {
            photoUpload.init();
        },

        // Expose modules
        utils: utils,
        upload: photoUpload
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    Photo.init();
});
