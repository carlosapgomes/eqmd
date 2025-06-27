/**
 * Phase3Integration - Production-ready video compression integration
 * Combines all Phase 3 features: Error Handling, Performance Optimization, and Production Deployment
 */

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
        this.compressionQueue = [];
        this.activeCompressions = new Map();
        
        this.init();
    }

    /**
     * Initialize Phase 3 compression system
     */
    async init() {
        try {
            console.log('Initializing Phase 3 Video Compression System...');
            
            // Initialize core components
            await this.initializeComponents();
            
            // Setup medical context if provided
            if (this.options.medicalContext) {
                this.setMedicalContext(this.options.medicalContext);
            }
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Preload critical modules if enabled
            if (this.options.enableLazyLoading) {
                await this.preloadCriticalModules();
            }
            
            this.initialized = true;
            console.log('Phase 3 Video Compression System initialized successfully');
            
            // Emit initialization event
            this.emit('initialized', { timestamp: Date.now() });
            
        } catch (error) {
            console.error('Failed to initialize Phase 3 compression:', error);
            this.handleInitializationError(error);
        }
    }

    /**
     * Initialize all components
     */
    async initializeComponents() {
        // Initialize feature flags
        if (this.options.enableFeatureFlags) {
            this.components.featureFlags = new CompressionFeatureFlags();
            await this.components.featureFlags.updateFlags();
        }

        // Initialize monitoring
        if (this.options.enableMonitoring) {
            this.components.monitoring = new CompressionMonitoring();
        }

        // Initialize error handler
        this.components.errorHandler = new CompressionErrorHandler();

        // Initialize performance monitor
        this.components.performanceMonitor = new CompressionPerformanceMonitor();

        // Initialize lazy loader
        if (this.options.enableLazyLoading) {
            this.components.lazyLoader = new CompressionLazyLoader();
        }

        console.log('All components initialized');
    }

    /**
     * Set medical context for prioritized handling
     */
    setMedicalContext(context) {
        this.medicalContext = context;
        
        // Update error handler
        if (this.components.errorHandler) {
            this.components.errorHandler.setMedicalContext(context);
        }
        
        // Log context change
        if (this.components.monitoring) {
            this.components.monitoring.trackEvent('medical_context_set', context);
        }
    }

    /**
     * Check if compression is available and recommended
     */
    async checkCompressionAvailability(file, options = {}) {
        const result = {
            available: false,
            recommended: false,
            reason: '',
            settings: null,
            warnings: []
        };

        try {
            // Check feature flags
            if (!this.isFeatureEnabled('compression_enabled', { 
                medicalPriority: this.medicalContext?.priority 
            })) {
                result.reason = 'Feature disabled';
                return result;
            }

            // Check if emergency bypass is active
            if (this.components.errorHandler?.shouldSkipCompression()) {
                result.reason = 'Emergency bypass active';
                result.available = true; // Direct upload available
                return result;
            }

            // Check mobile device capabilities
            if (this.components.performanceMonitor?.isMobileDevice) {
                const mobileCheck = this.components.performanceMonitor.shouldAllowCompressionOnMobile();
                if (!mobileCheck.allowed) {
                    result.reason = `Mobile limitation: ${mobileCheck.reason}`;
                    return result;
                }
                if (mobileCheck.warning) {
                    result.warnings.push(`Mobile warning: ${mobileCheck.warning}`);
                }
            }

            // Check file size and type
            if (!this.isValidCompressionFile(file)) {
                result.reason = 'File not suitable for compression';
                return result;
            }

            // Load compression modules if needed
            if (this.components.lazyLoader) {
                const modulesLoaded = await this.loadCompressionModules(options);
                if (!modulesLoaded) {
                    result.reason = 'Failed to load compression modules';
                    return result;
                }
            }

            // Get optimized settings
            result.settings = this.getOptimizedSettings(file, options);
            
            // Determine if compression is recommended
            result.recommended = this.isCompressionRecommended(file, result.settings);
            result.available = true;
            result.reason = 'Compression available';

            return result;

        } catch (error) {
            console.error('Error checking compression availability:', error);
            result.reason = `Error: ${error.message}`;
            return result;
        }
    }

    /**
     * Compress video file with full Phase 3 features
     */
    async compressVideo(file, options = {}) {
        const compressionId = this.generateCompressionId();
        
        try {
            // Check availability first
            const availability = await this.checkCompressionAvailability(file, options);
            
            if (!availability.available) {
                throw new Error(`Compression not available: ${availability.reason}`);
            }

            // Start monitoring
            if (this.components.monitoring) {
                this.components.monitoring.startCompressionTracking(compressionId, {
                    fileSize: file.size,
                    fileName: file.name,
                    preset: options.preset,
                    medicalContext: this.medicalContext,
                    ...options
                });
            }

            // Start performance tracking
            if (this.components.performanceMonitor) {
                this.components.performanceMonitor.startCompressionTracking(compressionId, {
                    originalFile: file,
                    preset: options.preset
                });
            }

            // Add to active compressions
            this.activeCompressions.set(compressionId, {
                file,
                options,
                startTime: Date.now(),
                status: 'starting'
            });

            // Emit compression start event
            this.emit('compressionStarted', { compressionId, file, options });

            // Perform actual compression
            const result = await this.performCompression(compressionId, file, {
                ...options,
                settings: availability.settings
            });

            // Complete tracking
            if (this.components.monitoring) {
                this.components.monitoring.completeCompressionTracking(compressionId, result);
            }

            if (this.components.performanceMonitor) {
                this.components.performanceMonitor.completeCompressionTracking(compressionId, result);
            }

            // Clean up
            this.activeCompressions.delete(compressionId);

            // Emit completion event
            this.emit('compressionCompleted', { compressionId, result });

            return {
                success: true,
                compressionId,
                ...result
            };

        } catch (error) {
            console.error('Compression failed:', error);
            
            // Handle error through error handler
            const recovery = await this.handleCompressionError(compressionId, error, { file, options });
            
            if (recovery && recovery.success) {
                // Retry with recovery modifications
                return await this.compressVideo(file, { ...options, ...recovery.modifications });
            }

            // Complete tracking with error
            if (this.components.monitoring) {
                this.components.monitoring.completeCompressionTracking(compressionId, {
                    success: false,
                    error: error.message
                });
            }

            // Clean up
            this.activeCompressions.delete(compressionId);

            // Emit error event
            this.emit('compressionError', { compressionId, error });

            return {
                success: false,
                compressionId,
                error: error.message,
                fallback: recovery?.fallback || true
            };
        }
    }

    /**
     * Perform the actual compression
     */
    async performCompression(compressionId, file, options) {
        const stages = ['initializing', 'loading', 'processing', 'finalizing'];
        
        try {
            // Initialize compression
            this.updateCompressionStage(compressionId, 'initializing', 0);
            
            // Load worker and modules
            this.updateCompressionStage(compressionId, 'loading', 20);
            const worker = await this.getCompressionWorker();
            
            // Start processing
            this.updateCompressionStage(compressionId, 'processing', 30);
            
            const result = await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Compression timeout'));
                }, this.getCompressionTimeout(options));

                worker.postMessage({
                    type: 'compress',
                    compressionId,
                    file: file,
                    settings: options.settings
                });

                const handleMessage = (event) => {
                    const { type, data } = event.data;
                    
                    switch (type) {
                        case 'progress':
                            this.updateCompressionStage(compressionId, 'processing', 
                                30 + (data.progress * 0.6)); // 30-90%
                            break;
                            
                        case 'complete':
                            clearTimeout(timeout);
                            worker.removeEventListener('message', handleMessage);
                            this.updateCompressionStage(compressionId, 'finalizing', 95);
                            resolve(data);
                            break;
                            
                        case 'error':
                            clearTimeout(timeout);
                            worker.removeEventListener('message', handleMessage);
                            reject(new Error(data.message));
                            break;
                    }
                };

                worker.addEventListener('message', handleMessage);
            });

            // Finalize
            this.updateCompressionStage(compressionId, 'completed', 100);
            
            return {
                success: true,
                compressedFile: result.compressedFile,
                originalSize: file.size,
                compressedSize: result.size,
                compressionRatio: 1 - (result.size / file.size),
                duration: Date.now() - this.activeCompressions.get(compressionId).startTime
            };

        } catch (error) {
            this.updateCompressionStage(compressionId, 'error', 0, { error: error.message });
            throw error;
        }
    }

    /**
     * Handle compression error with recovery
     */
    async handleCompressionError(compressionId, error, context) {
        if (!this.components.errorHandler) {
            return { success: false, fallback: true };
        }

        // Track error
        if (this.components.monitoring) {
            this.components.monitoring.trackCompressionError(compressionId, error, context);
        }

        // Attempt recovery
        const recovery = await this.components.errorHandler.handleError(error, context);
        
        // Track recovery attempt
        if (this.components.monitoring) {
            this.components.monitoring.trackErrorRecovery(compressionId, recovery);
        }

        return recovery;
    }

    /**
     * Update compression stage
     */
    updateCompressionStage(compressionId, stage, progress, data = {}) {
        // Update active compression
        const compression = this.activeCompressions.get(compressionId);
        if (compression) {
            compression.status = stage;
            compression.progress = progress;
        }

        // Update monitoring
        if (this.components.monitoring) {
            this.components.monitoring.updateCompressionStage(compressionId, stage, progress, data);
        }

        // Update performance monitor
        if (this.components.performanceMonitor) {
            this.components.performanceMonitor.updateCompressionStage(compressionId, stage, progress, data);
        }

        // Emit progress event
        this.emit('compressionProgress', { compressionId, stage, progress, data });
    }

    /**
     * Get optimized compression settings
     */
    getOptimizedSettings(file, options) {
        let settings = {
            preset: options.preset || 'medical-standard',
            quality: options.quality || 'balanced',
            maxDuration: 60000, // 1 minute default
            chunkSize: 32 * 1024 * 1024 // 32MB chunks
        };

        // Apply mobile optimizations
        if (this.components.performanceMonitor?.isMobileDevice) {
            const mobileSettings = this.components.performanceMonitor.getMobileOptimizedSettings();
            if (mobileSettings) {
                settings = { ...settings, ...mobileSettings };
            }
        }

        // Apply medical context optimizations
        if (this.medicalContext) {
            switch (this.medicalContext.priority) {
                case 'emergency':
                    settings.preset = 'mobile-fast';
                    settings.maxDuration = 15000;
                    settings.quality = 'speed';
                    break;
                case 'urgent':
                    settings.preset = 'mobile-optimized';
                    settings.maxDuration = 30000;
                    settings.quality = 'balanced';
                    break;
            }
        }

        // Apply feature flag modifications
        if (this.isFeatureEnabled('advanced_compression')) {
            settings.advancedCodecs = true;
        }

        return settings;
    }

    /**
     * Check if compression is recommended for this file
     */
    isCompressionRecommended(file, settings) {
        // Always recommend for large files
        if (file.size > 100 * 1024 * 1024) { // > 100MB
            return true;
        }

        // Check network conditions
        const connection = navigator.connection;
        if (connection) {
            // Recommend on slow networks
            if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                return true;
            }
            
            // Don't recommend on fast networks for small files
            if (connection.effectiveType === '4g' && file.size < 10 * 1024 * 1024) {
                return false;
            }
        }

        // Recommend for mobile devices
        if (this.components.performanceMonitor?.isMobileDevice) {
            return file.size > 25 * 1024 * 1024; // > 25MB on mobile
        }

        // Default recommendation
        return file.size > 50 * 1024 * 1024; // > 50MB
    }

    /**
     * Check if file is valid for compression
     */
    isValidCompressionFile(file) {
        const validTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/webm'];
        const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
        const minSize = 1 * 1024 * 1024; // 1MB

        return validTypes.includes(file.type) && 
               file.size >= minSize && 
               file.size <= maxSize;
    }

    /**
     * Load compression modules based on requirements
     */
    async loadCompressionModules(options) {
        if (!this.components.lazyLoader) return true;

        try {
            const useCase = this.determineUseCase(options);
            const results = await this.components.lazyLoader.loadForUseCase(useCase);
            return results.every(Boolean);
        } catch (error) {
            console.error('Failed to load compression modules:', error);
            return false;
        }
    }

    /**
     * Determine use case for module loading
     */
    determineUseCase(options) {
        if (this.isFeatureEnabled('advanced_compression')) {
            return 'advanced_compression';
        }
        
        if (this.medicalContext) {
            return 'medical_workflow';
        }
        
        return 'basic_compression';
    }

    /**
     * Get compression worker
     */
    async getCompressionWorker() {
        // Reuse existing worker or create new one
        if (!this.compressionWorker) {
            this.compressionWorker = new Worker('/static/mediafiles/js/compression/workers/compression-worker.js');
        }
        return this.compressionWorker;
    }

    /**
     * Get compression timeout based on context
     */
    getCompressionTimeout(options) {
        if (this.medicalContext?.priority === 'emergency') {
            return 15000; // 15 seconds for emergency
        }
        
        if (this.medicalContext?.priority === 'urgent') {
            return 30000; // 30 seconds for urgent
        }
        
        if (this.components.performanceMonitor?.isMobileDevice) {
            return 45000; // 45 seconds for mobile
        }
        
        return 120000; // 2 minutes default
    }

    /**
     * Check if feature is enabled
     */
    isFeatureEnabled(featureName, context = {}) {
        if (!this.components.featureFlags) return true; // Default to enabled
        
        return this.components.featureFlags.isEnabled(featureName, context);
    }

    /**
     * Get feature variant
     */
    getFeatureVariant(featureName, context = {}) {
        if (!this.components.featureFlags) return null;
        
        return this.components.featureFlags.getVariant(featureName, context);
    }

    /**
     * Activate emergency bypass
     */
    activateEmergencyBypass(reason) {
        if (this.components.errorHandler) {
            this.components.errorHandler.activateEmergencyBypass(reason);
        }
        
        if (this.components.featureFlags) {
            this.components.featureFlags.emergencyDisable(reason);
        }
        
        this.emit('emergencyBypass', { reason, timestamp: Date.now() });
    }

    /**
     * Preload critical modules
     */
    async preloadCriticalModules() {
        if (!this.components.lazyLoader) return true;
        
        try {
            return await this.components.lazyLoader.preloadCriticalModules();
        } catch (error) {
            console.warn('Failed to preload critical modules:', error);
            return false;
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for network changes
        window.addEventListener('online', () => {
            this.emit('networkChange', { online: true });
        });
        
        window.addEventListener('offline', () => {
            this.emit('networkChange', { online: false });
        });

        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.emit('visibilityChange', { hidden: document.hidden });
        });

        // Listen for performance warnings
        window.addEventListener('compression-performance-warning', (event) => {
            this.emit('performanceWarning', event.detail);
        });

        // Listen for low battery warnings
        window.addEventListener('compression-low-battery', (event) => {
            this.emit('lowBattery', event.detail);
        });

        // Listen for thermal throttling
        window.addEventListener('compression-thermal-throttling', (event) => {
            this.emit('thermalThrottling', event.detail);
        });
    }

    /**
     * Handle initialization error
     */
    handleInitializationError(error) {
        console.error('Initialization failed:', error);
        
        // Fallback mode - disable all advanced features
        this.options.enableFeatureFlags = false;
        this.options.enableMonitoring = false;
        this.options.enableLazyLoading = false;
        
        this.emit('initializationError', { error, fallbackMode: true });
    }

    /**
     * Generate unique compression ID
     */
    generateCompressionId() {
        return `compression_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get system status
     */
    getSystemStatus() {
        return {
            initialized: this.initialized,
            activeCompressions: this.activeCompressions.size,
            components: {
                featureFlags: !!this.components.featureFlags,
                monitoring: !!this.components.monitoring,
                errorHandler: !!this.components.errorHandler,
                performanceMonitor: !!this.components.performanceMonitor,
                lazyLoader: !!this.components.lazyLoader
            },
            medicalContext: this.medicalContext,
            options: this.options
        };
    }

    /**
     * Get detailed metrics and statistics
     */
    getDetailedMetrics() {
        const metrics = {
            systemStatus: this.getSystemStatus(),
            activeCompressions: Array.from(this.activeCompressions.entries())
        };

        if (this.components.monitoring) {
            metrics.monitoring = this.components.monitoring.getStatistics();
        }

        if (this.components.performanceMonitor) {
            metrics.performance = this.components.performanceMonitor.getCompressionStats();
        }

        if (this.components.errorHandler) {
            metrics.errors = this.components.errorHandler.getErrorStats();
        }

        if (this.components.featureFlags) {
            metrics.featureFlags = this.components.featureFlags.getDebugInfo();
        }

        return metrics;
    }

    /**
     * Simple event emitter functionality
     */
    emit(eventType, data) {
        const event = new CustomEvent(`videoCompression:${eventType}`, {
            detail: data
        });
        window.dispatchEvent(event);
    }

    /**
     * Clean up all components
     */
    cleanup() {
        // Clean up active compressions
        this.activeCompressions.clear();
        
        // Clean up components
        Object.values(this.components).forEach(component => {
            if (component.cleanup) {
                component.cleanup();
            }
        });
        
        // Clean up worker
        if (this.compressionWorker) {
            this.compressionWorker.terminate();
        }
        
        this.initialized = false;
        
        console.log('Phase 3 Video Compression System cleaned up');
    }
}

// Export for global use
window.VideoCompressionPhase3 = VideoCompressionPhase3;