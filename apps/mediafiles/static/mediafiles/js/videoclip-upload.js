/**
 * VideoClip Upload - JavaScript for EquipeMed MediaFiles
 * 
 * Handles video upload, preview, validation, and compression functionality
 * Implements video upload functionality following photo.js patterns
 */

// VideoClip namespace for upload functionality
(function() {
    'use strict';

    // Video-specific configuration (extends MediaFiles config)
    const config = {
        maxVideoDuration: 120, // 2 minutes in seconds
        maxVideoSize: 50 * 1024 * 1024, // 50MB
        allowedVideoTypes: ['video/mp4', 'video/webm', 'video/quicktime'],
        allowedVideoExtensions: ['.mp4', '.webm', '.mov'],
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
        },
        formatDuration: function(seconds) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.floor(seconds % 60);
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
    };

    // Video upload handler
    const videoUpload = {
        // Compression properties
        compressionManager: null,
        compressionControls: null,
        compressionEnabled: false,
        compressionPreset: 'medical-standard',
        emergencyMode: false,

        /**
         * Initialize video upload functionality
         */
        init: function() {
            this.setupDragAndDrop();
            this.setupFileInputs();
            this.setupPreviewControls();
            this.initCompression();
        },

        /**
         * Setup drag and drop functionality
         */
        setupDragAndDrop: function() {
            const uploadAreas = document.querySelectorAll('.video-upload-form, #uploadArea');
            
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
            const fileInputs = document.querySelectorAll('input[type="file"][accept*="video"]');
            
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
            const removeButtons = document.querySelectorAll('#removeVideo, .video-preview-remove');
            const changeButtons = document.querySelectorAll('.video-preview-change');

            removeButtons.forEach(btn => {
                btn.addEventListener('click', this.removePreview.bind(this));
            });

            changeButtons.forEach(btn => {
                btn.addEventListener('click', this.changeVideo.bind(this));
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
            if (!this.validateVideo(file)) {
                e.target.value = ''; // Clear the input
                return;
            }

            // Show upload progress
            this.showUploadProgress();

            // Process with compression if available
            if (this.compressionManager) {
                this.processVideoWithCompression(file, e.target);
            } else {
                this.processVideo(file, e.target);
            }
        },

        /**
         * Validate video file
         */
        validateVideo: function(file) {
            // Check file type
            if (!config.allowedVideoTypes.includes(file.type)) {
                utils.showToast('Tipo de arquivo não permitido. Use MP4, WebM ou MOV.', 'danger');
                return false;
            }

            // Check file extension
            const extension = '.' + utils.getFileExtension(file.name);
            if (!config.allowedVideoExtensions.includes(extension)) {
                utils.showToast('Extensão de arquivo não permitida.', 'danger');
                return false;
            }

            // Check file size
            if (file.size > config.maxVideoSize) {
                const maxSizeMB = config.maxVideoSize / (1024 * 1024);
                utils.showToast(`Arquivo muito grande. Máximo: ${maxSizeMB}MB`, 'danger');
                return false;
            }

            return true;
        },

        /**
         * Process video file
         */
        processVideo: function(file, input) {
            const video = document.createElement('video');
            video.preload = 'metadata';
            
            video.onloadedmetadata = () => {
                // Validate video duration
                if (video.duration > config.maxVideoDuration) {
                    const maxDurationFormatted = utils.formatDuration(config.maxVideoDuration);
                    utils.showToast(`Vídeo muito longo. Máximo: ${maxDurationFormatted}`, 'danger');
                    input.value = '';
                    this.hideUploadProgress();
                    return;
                }

                // Show preview
                this.showVideoPreview(URL.createObjectURL(file), file, video.duration);
                
                // Hide upload progress
                this.hideUploadProgress();
                
                // Show success message
                utils.showToast('Vídeo carregado com sucesso!', 'success');
            };

            video.onerror = () => {
                utils.showToast('Erro ao carregar o vídeo.', 'danger');
                input.value = '';
                this.hideUploadProgress();
            };

            video.src = URL.createObjectURL(file);
        },

        /**
         * Show video preview
         */
        showVideoPreview: function(videoSrc, file, duration) {
            const previewContainer = document.getElementById('videoPreview');
            const uploadForm = document.getElementById('uploadArea');
            
            if (!previewContainer) return;

            // Update preview video
            const previewVideo = previewContainer.querySelector('#previewVideo');
            if (previewVideo) {
                previewVideo.src = videoSrc;
            }

            // Update metadata
            this.updateVideoMetadata(file, duration);

            // Show preview, hide upload form
            previewContainer.style.display = 'block';
            if (uploadForm) {
                uploadForm.style.display = 'none';
            }
        },

        /**
         * Update video metadata display
         */
        updateVideoMetadata: function(file, duration) {
            const elements = {
                fileName: document.getElementById('fileName'),
                fileSize: document.getElementById('fileSize'),
                videoDuration: document.getElementById('videoDuration'),
                fileType: document.getElementById('fileType')
            };

            if (elements.fileName) elements.fileName.textContent = file.name;
            if (elements.fileSize) elements.fileSize.textContent = utils.formatFileSize(file.size);
            if (elements.videoDuration) elements.videoDuration.textContent = utils.formatDuration(duration);
            if (elements.fileType) elements.fileType.textContent = file.type;
        },

        /**
         * Remove video preview
         */
        removePreview: function(e) {
            e.preventDefault();
            
            const previewContainer = document.getElementById('videoPreview');
            const uploadForm = document.getElementById('uploadArea');
            const fileInput = document.querySelector('input[type="file"][accept*="video"]');

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
         * Change video (trigger file input)
         */
        changeVideo: function(e) {
            e.preventDefault();
            
            const fileInput = document.querySelector('input[type="file"][accept*="video"]');
            if (fileInput) {
                fileInput.click();
            }
        },

        /**
         * Show upload progress
         */
        showUploadProgress: function() {
            const progressContainer = document.getElementById('uploadProgress');
            if (progressContainer) {
                progressContainer.style.display = 'block';
                
                // Simulate progress
                const progressBar = progressContainer.querySelector('#progressBar');
                
                if (progressBar) {
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += Math.random() * 20; // Slower for videos
                        if (progress >= 100) {
                            progress = 100;
                            clearInterval(interval);
                        }
                        
                        progressBar.style.width = progress + '%';
                    }, 200);
                }
            }
        },

        /**
         * Hide upload progress
         */
        hideUploadProgress: function() {
            const progressContainer = document.getElementById('uploadProgress');
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        },

        /**
         * Initialize compression integration
         */
        initCompression: function() {
            // Check if compression is available
            if (window.VideoCompressionPhase3) {
                try {
                    this.compressionManager = new VideoCompressionPhase3({
                        enableFeatureFlags: true,
                        enableMonitoring: true,
                        enableLazyLoading: true
                    });
                    
                    // Initialize compression manager
                    this.compressionManager.init().then(() => {
                        this.setupCompressionControls();
                    }).catch(error => {
                        console.warn('Compression not available:', error);
                        this.setupFallbackUpload();
                    });
                } catch (error) {
                    console.warn('Failed to initialize compression manager:', error);
                    this.setupFallbackUpload();
                }
            } else {
                console.info('VideoCompressionPhase3 not available, using standard upload');
                this.setupFallbackUpload();
            }
        },

        /**
         * Setup compression controls UI
         */
        setupCompressionControls: function() {
            const uploadArea = document.getElementById('uploadArea');
            if (!uploadArea) return;

            // Check if CompressionControls is available
            if (typeof CompressionControls === 'undefined') {
                console.warn('CompressionControls not available, using fallback upload');
                this.setupFallbackUpload();
                return;
            }

            try {
                // Create controls container
                const controlsContainer = document.createElement('div');
                controlsContainer.className = 'compression-controls-container';
                controlsContainer.id = 'compressionControlsContainer';
                
                // Insert before upload area
                uploadArea.parentNode.insertBefore(controlsContainer, uploadArea);

                // Initialize compression controls
                this.compressionControls = new CompressionControls(controlsContainer, {
                    medicalContext: this.getMedicalContext()
                });

                // Setup event handlers
                this.setupCompressionEventHandlers();
                
                console.log('Compression controls initialized successfully');
            } catch (error) {
                console.warn('Failed to setup compression controls:', error);
                this.setupFallbackUpload();
            }
        },

        /**
         * Setup compression event handlers
         */
        setupCompressionEventHandlers: function() {
            const container = document.getElementById('compressionControlsContainer');
            if (!container) return;
            
            container.addEventListener('compression:compressionEnabled', (e) => {
                this.compressionEnabled = true;
                this.compressionPreset = e.detail.preset;
            });

            container.addEventListener('compression:compressionDisabled', () => {
                this.compressionEnabled = false;
            });

            container.addEventListener('compression:presetSelected', (e) => {
                this.compressionPreset = e.detail.preset;
            });

            container.addEventListener('compression:emergencyBypass', () => {
                this.compressionEnabled = false;
                this.emergencyMode = true;
            });

            container.addEventListener('compression:compressionCancelled', () => {
                this.fallbackToDirectUpload();
            });
        },

        /**
         * Enhanced file processing with compression
         */
        processVideoWithCompression: async function(file, input) {
            if (!this.compressionEnabled || this.emergencyMode) {
                return this.processVideo(file, input); // Use existing method
            }

            try {
                // Check compression availability
                const availability = await this.compressionManager.checkCompressionAvailability(file, {
                    preset: this.compressionPreset
                });

                if (!availability.available) {
                    console.warn('Compression not available:', availability.reason);
                    return this.processVideo(file, input);
                }

                // Start compression
                const result = await this.compressVideoFile(file);
                
                if (result.success) {
                    // Use compressed file
                    this.compressionControls.completeCompression(result);
                    this.showVideoPreview(URL.createObjectURL(result.compressedFile), result.compressedFile, result.duration);
                } else {
                    // Fall back to original file
                    this.compressionControls.handleCompressionError(new Error(result.error));
                    this.processVideo(file, input);
                }
            } catch (error) {
                console.error('Compression failed:', error);
                if (this.compressionControls) {
                    this.compressionControls.handleCompressionError(error);
                }
                this.processVideo(file, input);
            }
        },

        /**
         * Compress video file
         */
        compressVideoFile: async function(file) {
            return await this.compressionManager.compressVideo(file, {
                preset: this.compressionPreset,
                onProgress: (data) => {
                    if (this.compressionControls) {
                        this.compressionControls.updateProgress(
                            data.stage, 
                            data.progress, 
                            data.eta
                        );
                    }
                }
            });
        },

        /**
         * Get medical context from page
         */
        getMedicalContext: function() {
            // Extract medical context from page data
            const patientElement = document.querySelector('[data-patient-id]');
            const priorityElement = document.querySelector('[data-medical-priority]');
            
            return {
                patientId: patientElement?.dataset.patientId,
                priority: priorityElement?.dataset.medicalPriority || 'routine',
                specialty: priorityElement?.dataset.specialty || 'general'
            };
        },

        /**
         * Fallback to direct upload
         */
        fallbackToDirectUpload: function() {
            this.compressionEnabled = false;
            // Hide compression UI and proceed with normal upload
            const controlsContainer = document.getElementById('compressionControlsContainer');
            if (controlsContainer) {
                controlsContainer.style.display = 'none';
            }
        },

        /**
         * Setup fallback upload when compression is not available
         */
        setupFallbackUpload: function() {
            // Compression not available, continue with standard upload
            console.info('Video compression not available, using standard upload');
        }
    };

    // Public API - assign to window
    window.VideoClip = {
        /**
         * Initialize all video upload functionality
         */
        init: function() {
            videoUpload.init();
        },

        // Expose modules
        utils: utils,
        upload: videoUpload,
        config: config
    };
})();