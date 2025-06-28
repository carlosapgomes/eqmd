/**
 * VideoClip Compression Bundle - Unified compression functionality for EquipeMed
 * 
 * This file consolidates all compression-related functionality to simplify webpack bundle resolution
 * and eliminate complex dependency issues. It includes:
 * - Core upload functionality from videoclip-upload.js
 * - Phase 3 compression integration
 * - All compression utilities and components
 */

console.log('VideoClip Compression Bundle loading...');

// =============================================================================
// COMPRESSION UTILITIES - Consolidated from various compression/utils files
// =============================================================================

// Feature Flags functionality
class CompressionFeatureFlags {
    constructor() {
        this.flags = new Map();
        this.emergencyBypass = false;
    }

    async updateFlags() {
        // Simulate flag loading - in production this would be an API call
        const defaultFlags = {
            compression_enabled: true,
            advanced_compression: false,
            mobile_compression_optimized: true
        };
        
        Object.entries(defaultFlags).forEach(([key, value]) => {
            this.flags.set(key, value);
        });
    }

    isEnabled(featureName, context = {}) {
        if (this.emergencyBypass) return false;
        return this.flags.get(featureName) || false;
    }

    emergencyDisable(reason) {
        console.warn('Emergency bypass activated:', reason);
        this.emergencyBypass = true;
    }

    getDebugInfo() {
        return {
            flags: Object.fromEntries(this.flags),
            emergencyBypass: this.emergencyBypass
        };
    }
}

// Monitoring functionality
class CompressionMonitoring {
    constructor() {
        this.compressions = new Map();
        this.stats = {
            total: 0,
            successful: 0,
            failed: 0,
            totalBytes: 0,
            compressedBytes: 0
        };
    }

    startCompressionTracking(id, data) {
        this.compressions.set(id, {
            ...data,
            startTime: Date.now(),
            stage: 'starting'
        });
        this.stats.total++;
    }

    updateCompressionStage(id, stage, progress, data = {}) {
        const compression = this.compressions.get(id);
        if (compression) {
            compression.stage = stage;
            compression.progress = progress;
            compression.lastUpdate = Date.now();
        }
    }

    completeCompressionTracking(id, result) {
        const compression = this.compressions.get(id);
        if (compression) {
            if (result.success) {
                this.stats.successful++;
                this.stats.totalBytes += result.originalSize || 0;
                this.stats.compressedBytes += result.compressedSize || 0;
            } else {
                this.stats.failed++;
            }
            this.compressions.delete(id);
        }
    }

    trackEvent(eventName, data) {
        console.log('Monitoring event:', eventName, data);
    }

    trackCompressionError(id, error, context) {
        console.error('Compression error tracked:', { id, error, context });
    }

    trackErrorRecovery(id, recovery) {
        console.log('Error recovery tracked:', { id, recovery });
    }

    getStatistics() {
        return { ...this.stats };
    }
}

// Error Handler functionality
class CompressionErrorHandler {
    constructor() {
        this.emergencyBypass = false;
        this.medicalContext = null;
        this.errorStats = {
            total: 0,
            recovered: 0,
            bypassed: 0
        };
    }

    setMedicalContext(context) {
        this.medicalContext = context;
    }

    shouldSkipCompression() {
        return this.emergencyBypass;
    }

    async handleError(error, context) {
        this.errorStats.total++;
        
        // Simple recovery strategy
        if (error.message.includes('timeout')) {
            return {
                success: true,
                modifications: { timeout: 60000 },
                fallback: false
            };
        }

        return {
            success: false,
            fallback: true
        };
    }

    activateEmergencyBypass(reason) {
        this.emergencyBypass = true;
        this.errorStats.bypassed++;
        console.warn('Emergency bypass activated:', reason);
    }

    getErrorStats() {
        return { ...this.errorStats };
    }
}

// Performance Monitor functionality
class CompressionPerformanceMonitor {
    constructor() {
        this.compressions = new Map();
        this.isMobileDevice = this.detectMobileDevice();
        this.stats = {
            averageDuration: 0,
            totalCompressions: 0
        };
    }

    detectMobileDevice() {
        return /Mobi|Android/i.test(navigator.userAgent);
    }

    startCompressionTracking(id, data) {
        this.compressions.set(id, {
            ...data,
            startTime: performance.now()
        });
    }

    updateCompressionStage(id, stage, progress, data = {}) {
        const compression = this.compressions.get(id);
        if (compression) {
            compression.currentStage = stage;
            compression.progress = progress;
        }
    }

    completeCompressionTracking(id, result) {
        const compression = this.compressions.get(id);
        if (compression) {
            const duration = performance.now() - compression.startTime;
            this.updateAverageStats(duration);
            this.compressions.delete(id);
        }
    }

    updateAverageStats(duration) {
        this.stats.totalCompressions++;
        this.stats.averageDuration = 
            (this.stats.averageDuration * (this.stats.totalCompressions - 1) + duration) / 
            this.stats.totalCompressions;
    }

    shouldAllowCompressionOnMobile() {
        return {
            allowed: true,
            warning: this.isMobileDevice ? 'Compression may be slower on mobile' : null
        };
    }

    getMobileOptimizedSettings() {
        if (!this.isMobileDevice) return null;
        
        return {
            quality: 'mobile-optimized',
            maxDuration: 30000,
            chunkSize: 16 * 1024 * 1024 // 16MB chunks for mobile
        };
    }

    getCompressionStats() {
        return { ...this.stats };
    }
}

// Lazy Loader functionality
class CompressionLazyLoader {
    constructor() {
        this.loadedModules = new Set();
    }

    async loadForUseCase(useCase) {
        // Simulate module loading
        return [true];
    }

    async preloadCriticalModules() {
        return true;
    }
}

// Compression Controls UI
class CompressionControls {
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;
        this.enabled = false;
        this.preset = 'medical-standard';
        this.init();
    }

    init() {
        this.render();
        this.setupEventHandlers();
    }

    render() {
        this.container.innerHTML = `
            <div class="compression-controls mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="bi bi-film"></i>
                            Configurações de Compressão
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="enableCompression">
                            <label class="form-check-label" for="enableCompression">
                                Ativar compressão de vídeo
                            </label>
                        </div>
                        <div class="compression-options" style="display: none;">
                            <div class="mb-2">
                                <label for="compressionPreset" class="form-label">Preset:</label>
                                <select class="form-select form-select-sm" id="compressionPreset">
                                    <option value="medical-standard">Padrão Médico</option>
                                    <option value="mobile-fast">Rápido (Mobile)</option>
                                    <option value="mobile-optimized">Otimizado (Mobile)</option>
                                </select>
                            </div>
                            <div class="compression-progress" style="display: none;">
                                <div class="progress mb-2">
                                    <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                                </div>
                                <small class="text-muted compression-status">Preparando...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventHandlers() {
        const enableCheckbox = this.container.querySelector('#enableCompression');
        const presetSelect = this.container.querySelector('#compressionPreset');
        const optionsDiv = this.container.querySelector('.compression-options');

        enableCheckbox.addEventListener('change', (e) => {
            this.enabled = e.target.checked;
            optionsDiv.style.display = this.enabled ? 'block' : 'none';
            
            this.dispatchEvent(this.enabled ? 'compressionEnabled' : 'compressionDisabled', {
                preset: this.preset
            });
        });

        presetSelect.addEventListener('change', (e) => {
            this.preset = e.target.value;
            this.dispatchEvent('presetSelected', { preset: this.preset });
        });
    }

    updateProgress(stage, progress, eta) {
        const progressBar = this.container.querySelector('.progress-bar');
        const statusText = this.container.querySelector('.compression-status');
        const progressDiv = this.container.querySelector('.compression-progress');

        if (progressDiv) progressDiv.style.display = 'block';
        if (progressBar) progressBar.style.width = progress + '%';
        if (statusText) statusText.textContent = `${stage}... ${Math.round(progress)}%`;
    }

    completeCompression(result) {
        const statusText = this.container.querySelector('.compression-status');
        if (statusText) statusText.textContent = 'Compressão concluída!';
        
        setTimeout(() => {
            const progressDiv = this.container.querySelector('.compression-progress');
            if (progressDiv) progressDiv.style.display = 'none';
        }, 2000);
    }

    handleCompressionError(error) {
        console.error('[COMPRESSION UI] Handling compression error:', {
            error: error,
            errorMessage: error.message,
            errorStack: error.stack
        });

        const statusText = this.container.querySelector('.compression-status');
        if (statusText) {
            statusText.textContent = `Erro na compressão: ${error.message}`;
            statusText.classList.add('text-danger');
        }
        
        setTimeout(() => {
            const progressDiv = this.container.querySelector('.compression-progress');
            if (progressDiv) progressDiv.style.display = 'none';
            if (statusText) {
                statusText.textContent = 'Usando arquivo original';
                statusText.classList.remove('text-danger');
                statusText.classList.add('text-warning');
            }
        }, 5000); // Increased time to read error message
    }

    dispatchEvent(eventType, data) {
        const event = new CustomEvent(`compression:${eventType}`, { detail: data });
        this.container.dispatchEvent(event);
    }
}

// =============================================================================
// PHASE 3 INTEGRATION - Simplified version
// =============================================================================

class VideoCompressionPhase3 {
    constructor(options = {}) {
        this.options = {
            enableFeatureFlags: true,
            enableMonitoring: true,
            enableLazyLoading: true,
            medicalContext: null,
            ...options
        };

        this.initialized = false;
        this.components = {};
        this.activeCompressions = new Map();
    }

    async init() {
        try {
            console.log('Initializing Phase 3 Video Compression System...');
            
            // Initialize components
            this.components.featureFlags = new CompressionFeatureFlags();
            this.components.monitoring = new CompressionMonitoring();
            this.components.errorHandler = new CompressionErrorHandler();
            this.components.performanceMonitor = new CompressionPerformanceMonitor();
            this.components.lazyLoader = new CompressionLazyLoader();

            await this.components.featureFlags.updateFlags();
            
            this.initialized = true;
            console.log('Phase 3 Video Compression System initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Phase 3 compression:', error);
            this.initialized = false;
        }
    }

    async checkCompressionAvailability(file, options = {}) {
        console.log('[COMPRESSION DEBUG] Checking compression availability for file:', {
            name: file.name,
            type: file.type,
            size: file.size,
            sizeFormatted: this.formatFileSize(file.size),
            options: options
        });

        const result = {
            available: false,
            recommended: false,
            reason: '',
            settings: null
        };

        if (!this.initialized) {
            result.reason = 'System not initialized';
            console.error('[COMPRESSION DEBUG] System not initialized');
            return result;
        }

        const fileValidation = this.isValidCompressionFile(file);
        console.log('[COMPRESSION DEBUG] File validation result:', fileValidation);
        
        if (!fileValidation) {
            result.reason = 'File not suitable for compression';
            console.error('[COMPRESSION DEBUG] File validation failed:', {
                fileType: file.type,
                fileSize: file.size,
                validTypes: ['video/mp4', 'video/avi', 'video/mov', 'video/webm'],
                minSize: 1 * 1024 * 1024,
                maxSize: 2 * 1024 * 1024 * 1024
            });
            return result;
        }

        result.settings = this.getOptimizedSettings(file, options);
        result.recommended = this.isCompressionRecommended(file, result.settings);
        result.available = true;
        result.reason = 'Compression available';

        console.log('[COMPRESSION DEBUG] Compression availability check passed:', {
            available: result.available,
            recommended: result.recommended,
            settings: result.settings
        });

        return result;
    }

    async compressVideo(file, options = {}) {
        const compressionId = this.generateCompressionId();
        
        console.log('[COMPRESSION DEBUG] Starting compression process:', {
            compressionId: compressionId,
            fileName: file.name,
            fileType: file.type,
            fileSize: file.size,
            sizeFormatted: this.formatFileSize(file.size),
            preset: options.preset,
            options: options
        });
        
        try {
            console.log('[COMPRESSION DEBUG] Checking availability...');
            const availability = await this.checkCompressionAvailability(file, options);
            
            if (!availability.available) {
                const errorMsg = `Compression not available: ${availability.reason}`;
                console.error('[COMPRESSION DEBUG] Availability check failed:', {
                    reason: availability.reason,
                    availability: availability
                });
                throw new Error(errorMsg);
            }

            console.log('[COMPRESSION DEBUG] Starting compression tracking...');
            this.components.monitoring.startCompressionTracking(compressionId, {
                fileSize: file.size,
                fileName: file.name,
                preset: options.preset
            });

            this.activeCompressions.set(compressionId, {
                file,
                options,
                startTime: Date.now(),
                status: 'starting'
            });

            console.log('[COMPRESSION DEBUG] Performing compression...');
            // Simulate compression process
            const result = await this.performMockCompression(compressionId, file, options);

            console.log('[COMPRESSION DEBUG] Compression completed successfully:', {
                compressionId: compressionId,
                originalSize: result.originalSize,
                compressedSize: result.compressedSize,
                compressionRatio: result.compressionRatio,
                duration: result.duration
            });

            this.components.monitoring.completeCompressionTracking(compressionId, result);
            this.activeCompressions.delete(compressionId);

            return {
                success: true,
                compressionId,
                ...result
            };

        } catch (error) {
            console.error('[COMPRESSION DEBUG] Compression failed with error:', {
                compressionId: compressionId,
                error: error,
                errorMessage: error.message,
                errorStack: error.stack,
                fileName: file.name,
                fileType: file.type,
                fileSize: file.size
            });
            
            this.components.monitoring.completeCompressionTracking(compressionId, {
                success: false,
                error: error.message
            });

            this.activeCompressions.delete(compressionId);

            return {
                success: false,
                compressionId,
                error: error.message,
                fallback: true
            };
        }
    }

    async performMockCompression(compressionId, file, options) {
        console.log('[COMPRESSION DEBUG] Starting mock compression stages for:', compressionId);
        
        // Simulate compression stages
        const stages = ['initializing', 'loading', 'processing', 'finalizing'];
        
        try {
            for (let i = 0; i < stages.length; i++) {
                const progress = (i / stages.length) * 100;
                console.log(`[COMPRESSION DEBUG] Stage ${i + 1}/${stages.length}: ${stages[i]} (${Math.round(progress)}%)`);
                this.updateCompressionStage(compressionId, stages[i], progress);
                
                // Simulate processing time
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            // Simulate compression result (reduce file size by ~30%)
            const compressedSize = Math.floor(file.size * 0.7);
            const compressionRatio = 1 - (compressedSize / file.size);
            const duration = Date.now() - this.activeCompressions.get(compressionId).startTime;
            
            console.log('[COMPRESSION DEBUG] Mock compression completed:', {
                compressionId: compressionId,
                originalSize: file.size,
                compressedSize: compressedSize,
                compressionRatio: compressionRatio,
                duration: duration
            });
            
            return {
                success: true,
                compressedFile: file, // In real implementation, this would be the compressed file
                originalSize: file.size,
                compressedSize: compressedSize,
                compressionRatio: compressionRatio,
                duration: duration
            };
        } catch (error) {
            console.error('[COMPRESSION DEBUG] Mock compression failed:', {
                compressionId: compressionId,
                error: error,
                errorMessage: error.message
            });
            throw error;
        }
    }

    updateCompressionStage(compressionId, stage, progress, data = {}) {
        const compression = this.activeCompressions.get(compressionId);
        if (compression) {
            compression.status = stage;
            compression.progress = progress;
        }

        this.components.monitoring.updateCompressionStage(compressionId, stage, progress, data);
        this.components.performanceMonitor.updateCompressionStage(compressionId, stage, progress, data);

        // Call progress callback if provided
        const activeCompression = this.activeCompressions.get(compressionId);
        if (activeCompression && activeCompression.options.onProgress) {
            activeCompression.options.onProgress({ stage, progress, eta: null });
        }
    }

    getOptimizedSettings(file, options) {
        return {
            preset: options.preset || 'medical-standard',
            quality: options.quality || 'balanced',
            maxDuration: 60000,
            chunkSize: 32 * 1024 * 1024
        };
    }

    isCompressionRecommended(file, settings) {
        return file.size > 50 * 1024 * 1024; // > 50MB
    }

    isValidCompressionFile(file) {
        const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/webm'];
        const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
        const minSize = 1 * 1024 * 1024; // 1MB

        return validTypes.includes(file.type) && 
               file.size >= minSize && 
               file.size <= maxSize;
    }

    generateCompressionId() {
        return `compression_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// =============================================================================
// MAIN VIDEOCLIP UPLOAD FUNCTIONALITY
// =============================================================================

(function() {
    'use strict';
    
    console.log('VideoClip Compression IIFE executing...');

    // Video-specific configuration
    const config = {
        maxVideoDuration: 120, // 2 minutes in seconds
        maxVideoSize: 50 * 1024 * 1024, // 50MB
        allowedVideoTypes: ['video/mp4', 'video/webm', 'video/quicktime'],
        allowedVideoExtensions: ['.mp4', '.webm', '.mov'],
        previewMaxWidth: 800,
        previewMaxHeight: 600
    };

    // Use shared utilities from MediaFiles or provide fallbacks
    const utils = window.MediaFiles ? window.MediaFiles.utils : {
        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },
        getFileExtension: function(filename) {
            return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
        },
        showToast: function(message, type = 'info') {
            console.log(`Toast: ${message} (${type})`);
            // Fallback to basic notification
            if (window.bootstrap && window.bootstrap.Toast) {
                // Bootstrap toast implementation would go here
            } else {
                alert(message);
            }
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
            console.log('Initializing VideoClip upload functionality...');
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

            if (!this.validateVideo(file)) {
                e.target.value = '';
                return;
            }

            this.showUploadProgress();

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
            if (!config.allowedVideoTypes.includes(file.type)) {
                utils.showToast('Tipo de arquivo não permitido. Use MP4, WebM ou MOV.', 'danger');
                return false;
            }

            const extension = '.' + utils.getFileExtension(file.name);
            if (!config.allowedVideoExtensions.includes(extension)) {
                utils.showToast('Extensão de arquivo não permitida.', 'danger');
                return false;
            }

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
                if (video.duration > config.maxVideoDuration) {
                    const maxDurationFormatted = utils.formatDuration(config.maxVideoDuration);
                    utils.showToast(`Vídeo muito longo. Máximo: ${maxDurationFormatted}`, 'danger');
                    input.value = '';
                    this.hideUploadProgress();
                    return;
                }

                this.showVideoPreview(URL.createObjectURL(file), file, video.duration);
                this.hideUploadProgress();
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

            const previewVideo = previewContainer.querySelector('#previewVideo');
            if (previewVideo) {
                previewVideo.src = videoSrc;
            }

            this.updateVideoMetadata(file, duration);

            previewContainer.style.display = 'block';
            if (uploadForm) {
                uploadForm.style.display = 'none';
            }
        },

        /**
         * Show compressed video preview with proper metadata loading
         */
        showCompressedVideoPreview: function(compressedFile) {
            console.log('[UPLOAD DEBUG] Loading compressed video metadata...');
            console.log('[FRONTEND SIZE] Compressed file size:', {
                size: compressedFile.size,
                sizeFormatted: utils.formatFileSize(compressedFile.size),
                fileName: compressedFile.name,
                type: compressedFile.type
            });
            
            const video = document.createElement('video');
            video.preload = 'metadata';
            
            video.onloadedmetadata = () => {
                console.log('[UPLOAD DEBUG] Compressed video metadata loaded, duration:', video.duration);
                console.log('[FRONTEND SIZE] Final compressed video ready for upload:', {
                    fileName: compressedFile.name,
                    fileSize: compressedFile.size,
                    sizeFormatted: utils.formatFileSize(compressedFile.size),
                    duration: video.duration,
                    type: compressedFile.type
                });
                this.showVideoPreview(URL.createObjectURL(compressedFile), compressedFile, video.duration);
                this.hideUploadProgress();
                utils.showToast('Vídeo comprimido e carregado com sucesso!', 'success');
            };

            video.onerror = () => {
                console.error('[UPLOAD DEBUG] Failed to load compressed video metadata');
                utils.showToast('Erro ao carregar o vídeo comprimido.', 'danger');
                this.hideUploadProgress();
            };

            video.src = URL.createObjectURL(compressedFile);
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
            if (elements.videoDuration) {
                // Use local formatDuration function to avoid scoping issues
                const formatDuration = function(seconds) {
                    const minutes = Math.floor(seconds / 60);
                    const remainingSeconds = Math.floor(seconds % 60);
                    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
                };
                elements.videoDuration.textContent = formatDuration(duration);
            }
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

            if (fileInput) {
                fileInput.value = '';
            }

            if (previewContainer) {
                previewContainer.style.display = 'none';
            }
            if (uploadForm) {
                uploadForm.style.display = 'block';
            }

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
                
                const progressBar = progressContainer.querySelector('#progressBar');
                
                if (progressBar) {
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += Math.random() * 20;
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
            try {
                console.log('Initializing compression manager...');
                this.compressionManager = new VideoCompressionPhase3({
                    enableFeatureFlags: true,
                    enableMonitoring: true,
                    enableLazyLoading: true
                });
                
                this.compressionManager.init().then(() => {
                    console.log('Compression manager initialized successfully');
                    this.setupCompressionControls();
                }).catch(error => {
                    console.warn('Compression not available:', error);
                    this.setupFallbackUpload();
                });
            } catch (error) {
                console.warn('Failed to initialize compression manager:', error);
                this.setupFallbackUpload();
            }
        },

        /**
         * Setup compression controls UI
         */
        setupCompressionControls: function() {
            const uploadArea = document.getElementById('uploadArea');
            if (!uploadArea) return;

            try {
                const controlsContainer = document.createElement('div');
                controlsContainer.className = 'compression-controls-container';
                controlsContainer.id = 'compressionControlsContainer';
                
                uploadArea.parentNode.insertBefore(controlsContainer, uploadArea);

                this.compressionControls = new CompressionControls(controlsContainer, {
                    medicalContext: this.getMedicalContext()
                });

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
                console.log('[UPLOAD DEBUG] Compression enabled by user:', e.detail);
                this.compressionEnabled = true;
                this.compressionPreset = e.detail.preset;
            });

            container.addEventListener('compression:compressionDisabled', () => {
                console.log('[UPLOAD DEBUG] Compression disabled by user');
                this.compressionEnabled = false;
            });

            container.addEventListener('compression:presetSelected', (e) => {
                console.log('[UPLOAD DEBUG] Compression preset selected:', e.detail);
                this.compressionPreset = e.detail.preset;
            });
        },

        /**
         * Enhanced file processing with compression
         */
        processVideoWithCompression: async function(file, input) {
            console.log('[UPLOAD DEBUG] Processing video with compression:', {
                compressionEnabled: this.compressionEnabled,
                emergencyMode: this.emergencyMode,
                fileName: file.name,
                fileType: file.type,
                fileSize: file.size,
                preset: this.compressionPreset
            });

            if (!this.compressionEnabled || this.emergencyMode) {
                console.log('[UPLOAD DEBUG] Compression disabled or emergency mode, using standard upload');
                return this.processVideo(file, input);
            }

            try {
                console.log('[UPLOAD DEBUG] Checking compression availability...');
                const availability = await this.compressionManager.checkCompressionAvailability(file, {
                    preset: this.compressionPreset
                });

                console.log('[UPLOAD DEBUG] Availability check result:', availability);

                if (!availability.available) {
                    console.warn('[UPLOAD DEBUG] Compression not available:', availability.reason);
                    return this.processVideo(file, input);
                }

                console.log('[UPLOAD DEBUG] Starting compression process...');
                const result = await this.compressVideoFile(file);
                
                console.log('[UPLOAD DEBUG] Compression result:', {
                    success: result.success,
                    error: result.error,
                    compressionId: result.compressionId
                });
                
                if (result.success) {
                    console.log('[UPLOAD DEBUG] Compression successful, showing preview');
                    console.log('[FRONTEND SIZE] Compression results:', {
                        originalSize: result.originalSize,
                        originalSizeFormatted: utils.formatFileSize(result.originalSize),
                        compressedSize: result.compressedSize,
                        compressedSizeFormatted: utils.formatFileSize(result.compressedSize),
                        compressionRatio: result.compressionRatio,
                        sizeSavings: utils.formatFileSize(result.originalSize - result.compressedSize),
                        sizeSavingsPercent: Math.round(result.compressionRatio * 100) + '%'
                    });
                    this.compressionControls.completeCompression(result);
                    // Load video metadata to get correct duration before showing preview
                    this.showCompressedVideoPreview(result.compressedFile);
                } else {
                    console.error('[UPLOAD DEBUG] Compression failed, falling back to original:', result.error);
                    this.compressionControls.handleCompressionError(new Error(result.error));
                    this.processVideo(file, input);
                }
            } catch (error) {
                console.error('[UPLOAD DEBUG] Compression process threw exception:', {
                    error: error,
                    errorMessage: error.message,
                    errorStack: error.stack
                });
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
            const patientElement = document.querySelector('[data-patient-id]');
            const priorityElement = document.querySelector('[data-medical-priority]');
            
            return {
                patientId: patientElement?.dataset.patientId,
                priority: priorityElement?.dataset.medicalPriority || 'routine',
                specialty: priorityElement?.dataset.specialty || 'general'
            };
        },

        /**
         * Setup fallback upload when compression is not available
         */
        setupFallbackUpload: function() {
            console.info('Video compression not available, using standard upload');
        }
    };

    // Export classes to global scope
    window.VideoCompressionPhase3 = VideoCompressionPhase3;
    window.CompressionControls = CompressionControls;

    // Public API - assign to window
    console.log('VideoClip type before assignment:', typeof window.VideoClip);
    window.VideoClip = {
        /**
         * Initialize all video upload functionality
         */
        init: function() {
            console.log('VideoClip.init() called');
            videoUpload.init();
        },

        // Expose modules
        utils: utils,
        upload: videoUpload,
        config: config
    };
    console.log('VideoClip IIFE completed, window.VideoClip =', window.VideoClip);
    console.log('VideoClip type after assignment:', typeof window.VideoClip);
})();

console.log('VideoClip Compression Bundle fully loaded');