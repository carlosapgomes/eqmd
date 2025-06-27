/**
 * VideoCompression - Main integration module for Phase 1 video compression
 * Coordinates all compression components and provides simple API
 */

class VideoCompression {
    constructor() {
        this.manager = null;
        this.errorHandler = null;
        this.performanceMonitor = null;
        this.initialized = false;
        
        // Configuration
        this.config = {
            enabled: true,
            autoInitialize: false,
            debugMode: false
        };
        
        // Event callbacks
        this.callbacks = {
            onInitialized: null,
            onCapabilitiesDetected: null,
            onCompressionStart: null,
            onCompressionProgress: null,
            onCompressionComplete: null,
            onCompressionError: null,
            onFallback: null
        };
    }

    /**
     * Initialize the video compression system
     */
    async initialize(options = {}) {
        if (this.initialized) {
            return this.getCapabilities();
        }

        try {
            // Merge options with defaults
            this.config = { ...this.config, ...options };

            // Initialize components
            this.errorHandler = new CompressionErrorHandler();
            this.performanceMonitor = new CompressionPerformanceMonitor();
            this.manager = new VideoCompressionManager();

            // Set up manager callbacks
            this.setupManagerCallbacks();

            // Initialize the manager
            const capabilities = await this.manager.initialize();

            this.initialized = true;

            // Trigger callback
            if (this.callbacks.onInitialized) {
                this.callbacks.onInitialized(capabilities);
            }

            if (this.callbacks.onCapabilitiesDetected) {
                this.callbacks.onCapabilitiesDetected(capabilities);
            }

            if (this.config.debugMode) {
                console.log('Video compression initialized:', capabilities);
            }

            return capabilities;
        } catch (error) {
            console.error('Video compression initialization failed:', error);
            throw error;
        }
    }

    /**
     * Check if compression is available
     */
    isAvailable() {
        return this.initialized && this.manager?.isAvailable();
    }

    /**
     * Get current capabilities
     */
    getCapabilities() {
        return this.manager?.getCapabilities() || null;
    }

    /**
     * Compress a video file
     */
    async compressVideo(file, options = {}) {
        if (!this.isAvailable()) {
            throw new Error('Video compression not available');
        }

        const compressionId = this._generateId();
        
        try {
            // Start performance tracking
            this.performanceMonitor.startCompressionTracking(compressionId, options);

            // Trigger start callback
            if (this.callbacks.onCompressionStart) {
                this.callbacks.onCompressionStart({ file, options, compressionId });
            }

            // Perform compression
            const result = await this.manager.compressVideo(file, {
                ...options,
                compressionId
            });

            // Complete performance tracking
            this.performanceMonitor.completeCompressionTracking(compressionId, {
                originalSize: file.size,
                compressedSize: result.size,
                success: true
            });

            // Trigger completion callback
            if (this.callbacks.onCompressionComplete) {
                this.callbacks.onCompressionComplete({ 
                    original: file, 
                    compressed: result,
                    compressionId
                });
            }

            return result;
        } catch (error) {
            // Handle error with recovery attempts
            const errorResponse = await this.errorHandler.handleError(error, {
                file,
                options,
                compressionId
            });

            // Update performance tracking
            this.performanceMonitor.completeCompressionTracking(compressionId, {
                originalSize: file.size,
                success: false,
                error: error.message
            });

            // Trigger error callback
            if (this.callbacks.onCompressionError) {
                this.callbacks.onCompressionError({
                    error,
                    errorResponse,
                    file,
                    compressionId
                });
            }

            // If fallback is recommended, trigger fallback callback
            if (errorResponse.fallback && this.callbacks.onFallback) {
                this.callbacks.onFallback({
                    reason: errorResponse.errorType,
                    message: errorResponse.userMessage,
                    recommendations: errorResponse.recommendations,
                    originalFile: file,
                    compressionId
                });
            }

            throw error;
        }
    }

    /**
     * Cancel current compression
     */
    cancelCompression() {
        if (this.manager) {
            this.manager.cancelCompression();
        }
    }

    /**
     * Get available compression presets
     */
    getAvailablePresets() {
        return this.manager?.getAvailablePresets() || [];
    }

    /**
     * Get recommended preset for a file
     */
    getRecommendedPreset(file, userPreference = null) {
        return this.manager?.getRecommendedPreset(file, userPreference) || 'mobile-optimized';
    }

    /**
     * Estimate compression results
     */
    estimateCompression(file, preset = null) {
        return this.manager?.estimateCompression(file, preset) || null;
    }

    /**
     * Get performance recommendations
     */
    getRecommendations() {
        return this.performanceMonitor?.getPerformanceRecommendations() || [];
    }

    /**
     * Get compression statistics
     */
    getStats() {
        return {
            manager: this.manager?.getStats() || null,
            performance: this.performanceMonitor?.getCompressionStats() || null,
            errors: this.errorHandler?.getErrorStats() || null,
            initialized: this.initialized,
            available: this.isAvailable()
        };
    }

    /**
     * Set event callbacks
     */
    on(event, callback) {
        if (this.callbacks.hasOwnProperty(`on${event.charAt(0).toUpperCase()}${event.slice(1)}`)) {
            this.callbacks[`on${event.charAt(0).toUpperCase()}${event.slice(1)}`] = callback;
        } else {
            console.warn(`Unknown event: ${event}`);
        }
    }

    /**
     * Setup manager callbacks
     */
    setupManagerCallbacks() {
        if (!this.manager) return;

        this.manager.onProgress = (data) => {
            if (data.compressionId) {
                this.performanceMonitor.updateCompressionStage(
                    data.compressionId, 
                    data.stage, 
                    data.progress
                );
            }

            if (this.callbacks.onCompressionProgress) {
                this.callbacks.onCompressionProgress(data);
            }
        };

        this.manager.onComplete = (data) => {
            // Handled in compressVideo method
        };

        this.manager.onError = (data) => {
            // Handled in compressVideo method
        };

        this.manager.onFallback = (data) => {
            if (this.callbacks.onFallback) {
                this.callbacks.onFallback(data);
            }
        };
    }

    /**
     * Enable/disable compression
     */
    setEnabled(enabled) {
        this.config.enabled = enabled;
    }

    /**
     * Check if compression is enabled
     */
    isEnabled() {
        return this.config.enabled;
    }

    /**
     * Enable/disable debug mode
     */
    setDebugMode(enabled) {
        this.config.debugMode = enabled;
    }

    /**
     * Export performance data for analysis
     */
    exportPerformanceData() {
        return this.performanceMonitor?.exportPerformanceData() || null;
    }

    /**
     * Clear performance history
     */
    clearHistory() {
        this.performanceMonitor?.clearHistory();
        this.errorHandler?.clearErrorHistory();
    }

    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.manager) {
            this.manager.destroy();
        }
        if (this.performanceMonitor) {
            this.performanceMonitor.stopMonitoring();
        }
        
        this.manager = null;
        this.errorHandler = null;
        this.performanceMonitor = null;
        this.initialized = false;
    }

    // Private methods

    _generateId() {
        return 'vc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8);
    }
}

// Create global instance
window.videoCompression = new VideoCompression();

// Auto-initialize if configured
if (window.videoCompression.config.autoInitialize) {
    document.addEventListener('DOMContentLoaded', () => {
        window.videoCompression.initialize().catch(console.error);
    });
}

// Export class for manual instantiation
window.VideoCompression = VideoCompression;