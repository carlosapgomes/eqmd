/**
 * VideoCompressionManager - Main coordination for video compression
 * Part of Phase 1: Progressive Enhancement Framework
 */

class VideoCompressionManager {
    constructor() {
        this.detector = null;
        this.worker = null;
        this.initialized = false;
        this.capabilities = null;
        this.compressionInProgress = false;
        this.currentCompression = null;
        
        // Configuration
        this.config = {
            maxCompressionTime: 60000, // 60 seconds timeout
            maxRetries: 2,
            fallbackTimeout: 5000, // Quick fallback timeout
            workerPath: '/static/mediafiles/js/compression/workers/compression-worker.js'
        };

        // Event handlers
        this.onProgress = null;
        this.onComplete = null;
        this.onError = null;
        this.onFallback = null;
    }

    /**
     * Initialize the compression manager
     */
    async initialize() {
        if (this.initialized) {
            return this.capabilities;
        }

        try {
            // Initialize capability detector
            this.detector = new CompressionCapabilityDetector();
            this.capabilities = await this.detector.detectCapabilities();

            // Only proceed if compression is supported
            if (this.capabilities.supported) {
                await this._initializeWorker();
            }

            this.initialized = true;
            return this.capabilities;
        } catch (error) {
            console.warn('Compression manager initialization failed:', error);
            this.capabilities = this.detector?.getDefaultCapabilities() || this._getMinimalCapabilities();
            this.initialized = true;
            return this.capabilities;
        }
    }

    /**
     * Check if compression is available and recommended
     */
    isAvailable() {
        return this.initialized && this.capabilities?.supported;
    }

    /**
     * Get capability information
     */
    getCapabilities() {
        return this.capabilities;
    }

    /**
     * Compress a video file
     */
    async compressVideo(file, options = {}) {
        if (!this.isAvailable()) {
            throw new Error('Compression not available on this device');
        }

        if (this.compressionInProgress) {
            throw new Error('Compression already in progress');
        }

        const compressionId = this._generateCompressionId();
        this.compressionInProgress = true;
        this.currentCompression = {
            id: compressionId,
            file,
            options,
            startTime: Date.now(),
            retries: 0
        };

        try {
            return await this._performCompression(file, options);
        } catch (error) {
            console.error('Compression failed:', error);
            
            // Attempt recovery
            const recovered = await this._attemptRecovery(error);
            if (recovered) {
                return recovered;
            }
            
            // Trigger fallback
            this._triggerFallback(error);
            throw error;
        } finally {
            this.compressionInProgress = false;
            this.currentCompression = null;
        }
    }

    /**
     * Cancel current compression
     */
    cancelCompression() {
        if (this.compressionInProgress && this.worker) {
            this.worker.postMessage({ type: 'cancel' });
            this.compressionInProgress = false;
            this.currentCompression = null;
        }
    }

    /**
     * Get compression presets for current device
     */
    getAvailablePresets() {
        if (!this.capabilities) {
            return [];
        }
        return this.capabilities.recommendation.presets;
    }

    /**
     * Get recommended preset for file
     */
    getRecommendedPreset(file, userPreference = null) {
        const availablePresets = this.getAvailablePresets();
        
        if (userPreference && availablePresets.includes(userPreference)) {
            return userPreference;
        }

        // Smart preset selection based on file size and device capabilities
        const fileSizeMB = file.size / (1024 * 1024);
        const deviceScore = this.capabilities.score;

        if (fileSizeMB > 100 && deviceScore >= 80) {
            return 'medical-high';
        } else if (fileSizeMB > 50 && deviceScore >= 60) {
            return 'standard-medical';
        } else {
            return 'mobile-optimized';
        }
    }

    /**
     * Estimate compression time and size reduction
     */
    estimateCompression(file, preset = null) {
        const actualPreset = preset || this.getRecommendedPreset(file);
        const fileSizeMB = file.size / (1024 * 1024);
        const deviceScore = this.capabilities.score;

        // Rough estimates based on preset and device performance
        const estimates = {
            'medical-high': { timeMultiplier: 1.5, sizeReduction: 0.3 },
            'standard-medical': { timeMultiplier: 1.0, sizeReduction: 0.5 },
            'mobile-optimized': { timeMultiplier: 0.7, sizeReduction: 0.7 }
        };

        const presetConfig = estimates[actualPreset] || estimates['mobile-optimized'];
        
        // Base time estimate: ~1MB per 2 seconds on mid-range device
        const baseTimeSeconds = (fileSizeMB * 2) * presetConfig.timeMultiplier;
        const deviceAdjustment = deviceScore / 70; // Normalize to mid-range (70)
        const estimatedTimeSeconds = baseTimeSeconds / deviceAdjustment;

        const originalSizeMB = fileSizeMB;
        const compressedSizeMB = originalSizeMB * (1 - presetConfig.sizeReduction);

        return {
            estimatedTime: Math.round(estimatedTimeSeconds),
            originalSize: originalSizeMB,
            compressedSize: compressedSizeMB,
            sizeReduction: presetConfig.sizeReduction,
            preset: actualPreset
        };
    }

    // Private methods

    async _initializeWorker() {
        return new Promise((resolve, reject) => {
            try {
                this.worker = new Worker(this.config.workerPath);
                
                this.worker.onmessage = (event) => {
                    this._handleWorkerMessage(event);
                };

                this.worker.onerror = (error) => {
                    console.error('Worker error:', error);
                    reject(error);
                };

                // Test worker initialization
                this.worker.postMessage({ type: 'init' });
                
                // Resolve after brief delay to allow worker initialization
                setTimeout(() => resolve(), 100);
            } catch (error) {
                reject(error);
            }
        });
    }

    async _performCompression(file, options) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Compression timeout'));
            }, this.config.maxCompressionTime);

            const compressionHandlers = {
                progress: (data) => {
                    if (this.onProgress) {
                        this.onProgress(data);
                    }
                },
                complete: (data) => {
                    clearTimeout(timeout);
                    if (this.onComplete) {
                        this.onComplete(data);
                    }
                    resolve(data.compressedFile);
                },
                error: (data) => {
                    clearTimeout(timeout);
                    if (this.onError) {
                        this.onError(data);
                    }
                    reject(new Error(data.message));
                }
            };

            // Store handlers for worker message handling
            this._compressionHandlers = compressionHandlers;

            // Send compression request to worker
            this.worker.postMessage({
                type: 'compress',
                file: file,
                options: {
                    preset: this.getRecommendedPreset(file, options.preset),
                    maxOutputSize: options.maxOutputSize || file.size * 0.8,
                    ...options
                }
            });
        });
    }

    _handleWorkerMessage(event) {
        const { type, data } = event.data;

        if (this._compressionHandlers) {
            switch (type) {
                case 'progress':
                    this._compressionHandlers.progress(data);
                    break;
                case 'complete':
                    this._compressionHandlers.complete(data);
                    break;
                case 'error':
                    this._compressionHandlers.error(data);
                    break;
            }
        }
    }

    async _attemptRecovery(error) {
        if (!this.currentCompression || this.currentCompression.retries >= this.config.maxRetries) {
            return null;
        }

        console.log(`Attempting compression recovery (attempt ${this.currentCompression.retries + 1})`);
        this.currentCompression.retries++;

        try {
            // Try with lower quality settings
            const fallbackOptions = {
                ...this.currentCompression.options,
                preset: 'mobile-optimized',
                maxOutputSize: this.currentCompression.file.size * 0.9
            };

            return await this._performCompression(this.currentCompression.file, fallbackOptions);
        } catch (recoveryError) {
            console.warn('Recovery attempt failed:', recoveryError);
            return null;
        }
    }

    _triggerFallback(error) {
        if (this.onFallback) {
            this.onFallback({
                reason: error.message,
                originalFile: this.currentCompression?.file,
                recommendedAction: 'proceed-with-direct-upload'
            });
        }
    }

    _generateCompressionId() {
        return 'compression_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    _getMinimalCapabilities() {
        return {
            supported: false,
            score: 0,
            recommendation: {
                level: 'not-recommended',
                message: 'Compression not available',
                presets: []
            }
        };
    }

    /**
     * Cleanup resources
     */
    destroy() {
        if (this.worker) {
            this.worker.terminate();
            this.worker = null;
        }
        this.initialized = false;
        this.capabilities = null;
        this.compressionInProgress = false;
        this.currentCompression = null;
    }

    /**
     * Get compression statistics for analytics
     */
    getStats() {
        return {
            initialized: this.initialized,
            supported: this.isAvailable(),
            capabilities: this.capabilities,
            inProgress: this.compressionInProgress,
            currentCompression: this.currentCompression ? {
                id: this.currentCompression.id,
                duration: Date.now() - this.currentCompression.startTime,
                retries: this.currentCompression.retries
            } : null
        };
    }
}

// Export for use in other modules
window.VideoCompressionManager = VideoCompressionManager;