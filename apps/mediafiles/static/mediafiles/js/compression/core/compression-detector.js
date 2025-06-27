/**
 * CompressionCapabilityDetector - Detects device capabilities for video compression
 * Part of Phase 1: Foundation & Feature Detection
 */

class CompressionCapabilityDetector {
    constructor() {
        this.capabilities = null;
        this.detectionPromise = null;
    }

    /**
     * Main detection method - returns capability score (0-100)
     */
    async detectCapabilities() {
        if (this.detectionPromise) {
            return this.detectionPromise;
        }

        this.detectionPromise = this._performDetection();
        return this.detectionPromise;
    }

    async _performDetection() {
        try {
            const capabilities = {
                webAssembly: this._checkWebAssemblySupport(),
                webWorkers: this._checkWebWorkersSupport(),
                sharedArrayBuffer: this._checkSharedArrayBufferSupport(),
                memory: await this._estimateAvailableMemory(),
                cpuCores: this._getCPUCoreCount(),
                deviceClass: this._classifyDevice(),
                networkCondition: await this._assessNetworkCondition(),
                browserCompatibility: this._checkBrowserCompatibility()
            };

            const score = this._calculateCapabilityScore(capabilities);
            
            this.capabilities = {
                ...capabilities,
                score,
                supported: score >= 60, // Minimum threshold for compression support
                recommendation: this._getRecommendation(score, capabilities)
            };

            return this.capabilities;
        } catch (error) {
            console.warn('Compression capability detection failed:', error);
            return this._getDefaultCapabilities();
        }
    }

    /**
     * Check WebAssembly support
     */
    _checkWebAssemblySupport() {
        try {
            if (typeof WebAssembly === 'object' && 
                typeof WebAssembly.instantiate === 'function') {
                // Test with minimal WASM module
                const module = new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]);
                return WebAssembly.validate(module);
            }
            return false;
        } catch (e) {
            return false;
        }
    }

    /**
     * Check Web Workers support
     */
    _checkWebWorkersSupport() {
        return typeof Worker !== 'undefined';
    }

    /**
     * Check SharedArrayBuffer support (performance optimization)
     */
    _checkSharedArrayBufferSupport() {
        return typeof SharedArrayBuffer !== 'undefined';
    }

    /**
     * Estimate available memory
     */
    async _estimateAvailableMemory() {
        try {
            // Use Performance Memory API if available
            if ('memory' in performance) {
                const memInfo = performance.memory;
                return {
                    total: memInfo.jsHeapSizeLimit,
                    used: memInfo.usedJSHeapSize,
                    available: memInfo.jsHeapSizeLimit - memInfo.usedJSHeapSize,
                    sufficient: memInfo.jsHeapSizeLimit >= (2 * 1024 * 1024 * 1024) // 2GB minimum
                };
            }

            // Fallback: Estimate based on device characteristics
            return this._estimateMemoryFromDevice();
        } catch (e) {
            return this._estimateMemoryFromDevice();
        }
    }

    _estimateMemoryFromDevice() {
        const userAgent = navigator.userAgent.toLowerCase();
        let estimatedGB = 4; // Default assumption

        // iOS devices
        if (/iphone|ipad/.test(userAgent)) {
            if (/iphone.*1[4-9]|ipad.*1[0-9]/.test(userAgent)) {
                estimatedGB = 6; // Recent devices
            } else if (/iphone.*1[2-3]|ipad.*[8-9]/.test(userAgent)) {
                estimatedGB = 4; // Mid-range
            } else {
                estimatedGB = 2; // Older devices
            }
        }
        // Android devices
        else if (/android/.test(userAgent)) {
            // This is rough estimation - in practice, you'd want more sophisticated detection
            estimatedGB = 4;
        }

        const estimatedBytes = estimatedGB * 1024 * 1024 * 1024;
        return {
            total: estimatedBytes,
            used: estimatedBytes * 0.5, // Assume 50% usage
            available: estimatedBytes * 0.5,
            sufficient: estimatedGB >= 2
        };
    }

    /**
     * Get CPU core count
     */
    _getCPUCoreCount() {
        return navigator.hardwareConcurrency || 4; // Default to 4 if unknown
    }

    /**
     * Classify device performance level
     */
    _classifyDevice() {
        const userAgent = navigator.userAgent.toLowerCase();
        const cores = this._getCPUCoreCount();

        // High-end devices
        if (this._isHighEndDevice(userAgent)) {
            return { class: 'high-end', score: 90 };
        }
        
        // Mid-range devices
        if (cores >= 4) {
            return { class: 'mid-range', score: 70 };
        }

        // Low-end devices
        return { class: 'low-end', score: 30 };
    }

    _isHighEndDevice(userAgent) {
        // Recent iPhones
        if (/iphone.*1[4-9]/.test(userAgent)) return true;
        
        // Recent Samsung Galaxy devices
        if (/sm-s9[0-9]|sm-s2[0-9]/.test(userAgent)) return true;
        
        // Recent Google Pixel devices
        if (/pixel.*[6-9]/.test(userAgent)) return true;

        return false;
    }

    /**
     * Assess network conditions
     */
    async _assessNetworkCondition() {
        try {
            const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            
            if (connection) {
                return {
                    effectiveType: connection.effectiveType,
                    downlink: connection.downlink,
                    rtt: connection.rtt,
                    saveData: connection.saveData,
                    suitable: this._isNetworkSuitableForCompression(connection)
                };
            }

            // Fallback: Simple speed test
            return await this._performSimpleSpeedTest();
        } catch (e) {
            return { effectiveType: 'unknown', suitable: true };
        }
    }

    _isNetworkSuitableForCompression(connection) {
        // Compression beneficial on slower networks
        if (connection.saveData) return true;
        if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') return true;
        if (connection.effectiveType === '3g' && connection.downlink < 1.5) return true;
        
        return false; // Fast networks might not benefit from compression delay
    }

    async _performSimpleSpeedTest() {
        // Simple ping test to estimate network quality
        const startTime = performance.now();
        try {
            await fetch('/static/mediafiles/images/favicon.ico?' + Date.now(), { 
                method: 'HEAD',
                cache: 'no-cache'
            });
            const pingTime = performance.now() - startTime;
            
            return {
                effectiveType: pingTime > 500 ? 'slow' : 'fast',
                pingTime,
                suitable: pingTime > 200 // Slower networks benefit from compression
            };
        } catch (e) {
            return { effectiveType: 'unknown', suitable: true };
        }
    }

    /**
     * Check browser compatibility
     */
    _checkBrowserCompatibility() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        // Known problematic combinations
        const issues = [];
        
        // iOS Safari specific issues
        if (/safari/.test(userAgent) && /version\/1[2-4]/.test(userAgent)) {
            issues.push('ios-safari-wasm-issues');
        }
        
        // Old Chrome versions
        if (/chrome\/[1-7][0-9]/.test(userAgent)) {
            issues.push('old-chrome-wasm-support');
        }

        return {
            compatible: issues.length === 0,
            issues,
            score: issues.length === 0 ? 100 : Math.max(0, 100 - (issues.length * 25))
        };
    }

    /**
     * Calculate overall capability score (0-100)
     */
    _calculateCapabilityScore(capabilities) {
        let score = 0;
        let totalWeight = 0;

        // WebAssembly support (essential)
        if (capabilities.webAssembly) {
            score += 30;
        }
        totalWeight += 30;

        // Web Workers support (essential)
        if (capabilities.webWorkers) {
            score += 20;
        }
        totalWeight += 20;

        // Memory sufficiency
        if (capabilities.memory.sufficient) {
            score += 20;
        }
        totalWeight += 20;

        // Device class
        score += (capabilities.deviceClass.score * 0.15);
        totalWeight += 15;

        // Browser compatibility
        score += (capabilities.browserCompatibility.score * 0.10);
        totalWeight += 10;

        // SharedArrayBuffer (bonus)
        if (capabilities.sharedArrayBuffer) {
            score += 5;
        }
        totalWeight += 5;

        return Math.round((score / totalWeight) * 100);
    }

    /**
     * Get recommendation based on capabilities
     */
    _getRecommendation(score, capabilities) {
        if (score >= 80) {
            return {
                level: 'recommended',
                message: 'Device well-suited for video compression',
                presets: ['medical-high', 'standard-medical', 'mobile-optimized']
            };
        } else if (score >= 60) {
            return {
                level: 'conditional',
                message: 'Compression available with conservative settings',
                presets: ['standard-medical', 'mobile-optimized']
            };
        } else {
            return {
                level: 'not-recommended',
                message: 'Direct upload recommended for optimal experience',
                presets: []
            };
        }
    }

    /**
     * Get default capabilities for error cases
     */
    _getDefaultCapabilities() {
        return {
            webAssembly: false,
            webWorkers: false,
            sharedArrayBuffer: false,
            memory: { sufficient: false },
            cpuCores: 2,
            deviceClass: { class: 'low-end', score: 30 },
            networkCondition: { effectiveType: 'unknown', suitable: false },
            browserCompatibility: { compatible: false, issues: ['detection-failed'] },
            score: 0,
            supported: false,
            recommendation: {
                level: 'not-recommended',
                message: 'Compression not available due to capability detection failure',
                presets: []
            }
        };
    }

    /**
     * Get current capabilities (cached result)
     */
    getCapabilities() {
        return this.capabilities;
    }

    /**
     * Check if compression is supported
     */
    isSupported() {
        return this.capabilities?.supported || false;
    }

    /**
     * Get recommended presets for current device
     */
    getRecommendedPresets() {
        return this.capabilities?.recommendation?.presets || [];
    }
}

// Export for use in other modules
window.CompressionCapabilityDetector = CompressionCapabilityDetector;