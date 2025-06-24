/**
 * VideoClip-specific JavaScript for EquipeMed MediaFiles
 * 
 * Handles video upload, preview, validation, player controls, and modal interactions
 * Implements video functionality following photo.js patterns
 */

// VideoClip namespace
window.VideoClip = (function() {
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
        /**
         * Initialize video upload functionality
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

            // Process and show preview
            this.processVideo(file, e.target);
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
        }
    };

    // Video player controls
    const videoPlayer = {
        /**
         * Initialize video player functionality
         */
        init: function() {
            this.setupVideoPlayers();
            this.setupModalControls();
        },

        /**
         * Setup video players
         */
        setupVideoPlayers: function() {
            const videos = document.querySelectorAll('video');

            videos.forEach(video => {
                this.enhanceVideoPlayer(video);
            });
        },

        /**
         * Enhance individual video player
         */
        enhanceVideoPlayer: function(video) {
            // Add loading indicator
            video.addEventListener('loadstart', function() {
                this.style.cursor = 'wait';
            });

            video.addEventListener('canplay', function() {
                this.style.cursor = 'default';
            });

            // Error handling
            video.addEventListener('error', function() {
                console.error('Video loading error:', this.error);
                const errorMsg = document.createElement('div');
                errorMsg.className = 'alert alert-danger text-center';
                errorMsg.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>Erro ao carregar o vídeo. Tente novamente ou baixe o arquivo.';
                this.parentNode.replaceChild(errorMsg, this);
            });

            // Keyboard controls
            video.addEventListener('keydown', function(e) {
                switch(e.key) {
                    case ' ':
                        e.preventDefault();
                        if (this.paused) {
                            this.play();
                        } else {
                            this.pause();
                        }
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        this.currentTime = Math.max(0, this.currentTime - 10);
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        this.currentTime = Math.min(this.duration, this.currentTime + 10);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        this.volume = Math.min(1, this.volume + 0.1);
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        this.volume = Math.max(0, this.volume - 0.1);
                        break;
                    case 'm':
                    case 'M':
                        e.preventDefault();
                        this.muted = !this.muted;
                        break;
                }
            });

            // Add focus capability for keyboard navigation
            video.setAttribute('tabindex', '0');
        },

        /**
         * Setup modal controls
         */
        setupModalControls: function() {
            const videoModal = document.getElementById('videoModal');
            const modalVideo = document.getElementById('modalVideo');

            if (videoModal && modalVideo) {
                videoModal.addEventListener('shown.bs.modal', function() {
                    modalVideo.focus();
                });

                videoModal.addEventListener('hidden.bs.modal', function() {
                    modalVideo.pause();
                    modalVideo.currentTime = 0;
                });
            }
        }
    };

    // Public API
    return {
        /**
         * Initialize all video functionality
         */
        init: function() {
            videoUpload.init();
        },

        /**
         * Initialize video player functionality
         */
        initPlayer: function() {
            videoPlayer.init();
        },

        // Expose modules
        utils: utils,
        upload: videoUpload,
        player: videoPlayer,
        config: config
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    VideoClip.init();
});
