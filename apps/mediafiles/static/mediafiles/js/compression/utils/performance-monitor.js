/**
 * PerformanceMonitor - Performance tracking and optimization for video compression
 * Part of Phase 1: Memory Management System
 */

class CompressionPerformanceMonitor {
    constructor() {
        this.metrics = {
            compressions: [],
            deviceMetrics: {},
            performanceHistory: [],
            mobileOptimizations: {}
        };
        
        this.thresholds = {
            memoryUsage: 0.8, // 80% memory usage threshold
            batteryLevel: 0.15, // 15% battery threshold
            thermalState: 'nominal', // Thermal state threshold
            maxCompressions: 3, // Max concurrent compressions
            mobileMemoryUsage: 0.7, // Lower threshold for mobile devices
            mobileBatteryLevel: 0.25, // Higher threshold for mobile devices
            thermalThrottleTemp: 60 // Celsius
        };
        
        this.monitoring = false;
        this.monitoringInterval = null;
        this.isMobileDevice = this.detectMobileDevice();
        this.batteryMonitoring = false;
        this.thermalMonitoring = false;
        
        this.startMonitoring();
        this.setupMobileOptimizations();
    }

    /**
     * Start performance monitoring
     */
    startMonitoring() {
        if (this.monitoring) return;
        
        this.monitoring = true;
        this.collectInitialMetrics();
        
        // Monitor every 10 seconds
        this.monitoringInterval = setInterval(() => {
            this.collectPerformanceMetrics();
        }, 10000);
    }

    /**
     * Stop performance monitoring
     */
    stopMonitoring() {
        this.monitoring = false;
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
    }

    /**
     * Collect initial device metrics
     */
    async collectInitialMetrics() {
        this.metrics.deviceMetrics = {
            timestamp: Date.now(),
            userAgent: navigator.userAgent,
            hardwareConcurrency: navigator.hardwareConcurrency || 4,
            deviceMemory: navigator.deviceMemory || null,
            connection: this.getConnectionInfo(),
            platform: navigator.platform,
            maxTouchPoints: navigator.maxTouchPoints || 0
        };

        // Collect battery info if available
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                this.metrics.deviceMetrics.battery = {
                    level: battery.level,
                    charging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime
                };
            } catch (e) {
                console.warn('Battery API not available:', e);
            }
        }
    }

    /**
     * Collect ongoing performance metrics
     */
    collectPerformanceMetrics() {
        const metrics = {
            timestamp: Date.now(),
            memory: this.getMemoryMetrics(),
            performance: this.getPerformanceMetrics(),
            thermal: this.getThermalMetrics(),
            network: this.getNetworkMetrics()
        };

        this.metrics.performanceHistory.push(metrics);
        
        // Keep only last 100 entries
        if (this.metrics.performanceHistory.length > 100) {
            this.metrics.performanceHistory.shift();
        }

        // Check for performance issues
        this.checkPerformanceThresholds(metrics);
    }

    /**
     * Get memory metrics
     */
    getMemoryMetrics() {
        const memory = {
            available: false,
            jsHeapSizeLimit: 0,
            totalJSHeapSize: 0,
            usedJSHeapSize: 0,
            usageRatio: 0
        };

        if ('memory' in performance) {
            const memInfo = performance.memory;
            memory.available = true;
            memory.jsHeapSizeLimit = memInfo.jsHeapSizeLimit;
            memory.totalJSHeapSize = memInfo.totalJSHeapSize;
            memory.usedJSHeapSize = memInfo.usedJSHeapSize;
            memory.usageRatio = memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit;
        }

        return memory;
    }

    /**
     * Get performance timing metrics
     */
    getPerformanceMetrics() {
        const timing = performance.timing;
        const navigation = performance.navigation;
        
        return {
            navigationStart: timing.navigationStart,
            loadEventEnd: timing.loadEventEnd,
            domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
            pageLoadTime: timing.loadEventEnd - timing.navigationStart,
            navigationType: navigation.type,
            redirectCount: navigation.redirectCount
        };
    }

    /**
     * Get thermal state metrics (where available)
     */
    getThermalMetrics() {
        // Thermal state is not widely supported yet, but prepare for future
        return {
            available: false,
            state: 'unknown'
        };
    }

    /**
     * Get network metrics
     */
    getNetworkMetrics() {
        return this.getConnectionInfo();
    }

    /**
     * Get connection information
     */
    getConnectionInfo() {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        
        if (connection) {
            return {
                available: true,
                effectiveType: connection.effectiveType,
                downlink: connection.downlink,
                downlinkMax: connection.downlinkMax,
                rtt: connection.rtt,
                type: connection.type,
                saveData: connection.saveData
            };
        }

        return { available: false };
    }

    /**
     * Check performance thresholds and trigger warnings
     */
    checkPerformanceThresholds(metrics) {
        const warnings = [];

        // Memory usage check
        if (metrics.memory.available && metrics.memory.usageRatio > this.thresholds.memoryUsage) {
            warnings.push({
                type: 'memory_pressure',
                severity: 'high',
                message: `Memory usage at ${(metrics.memory.usageRatio * 100).toFixed(1)}%`,
                recommendation: 'Consider reducing compression quality or direct upload'
            });
        }

        // Network quality check
        if (metrics.network.available) {
            if (metrics.network.effectiveType === 'slow-2g' || metrics.network.effectiveType === '2g') {
                warnings.push({
                    type: 'slow_network',
                    severity: 'medium',
                    message: 'Slow network detected',
                    recommendation: 'Compression may take longer but will reduce upload time'
                });
            }
        }

        // Process warnings
        if (warnings.length > 0) {
            this.processPerformanceWarnings(warnings);
        }
    }

    /**
     * Process performance warnings
     */
    processPerformanceWarnings(warnings) {
        warnings.forEach(warning => {
            console.warn('Performance warning:', warning);
            
            // Emit custom event for UI to handle
            window.dispatchEvent(new CustomEvent('compression-performance-warning', {
                detail: warning
            }));
        });
    }

    /**
     * Start tracking a compression operation
     */
    startCompressionTracking(compressionId, options = {}) {
        const compressionMetrics = {
            id: compressionId,
            startTime: Date.now(),
            options,
            initialMetrics: {
                memory: this.getMemoryMetrics(),
                performance: this.getPerformanceMetrics()
            },
            stages: [],
            completed: false
        };

        this.metrics.compressions.push(compressionMetrics);
        return compressionMetrics;
    }

    /**
     * Update compression stage
     */
    updateCompressionStage(compressionId, stage, progress = 0, additionalData = {}) {
        const compression = this.metrics.compressions.find(c => c.id === compressionId);
        
        if (compression) {
            compression.stages.push({
                stage,
                progress,
                timestamp: Date.now(),
                duration: Date.now() - compression.startTime,
                metrics: {
                    memory: this.getMemoryMetrics()
                },
                ...additionalData
            });
        }
    }

    /**
     * Complete compression tracking
     */
    completeCompressionTracking(compressionId, result = {}) {
        const compression = this.metrics.compressions.find(c => c.id === compressionId);
        
        if (compression) {
            compression.completed = true;
            compression.endTime = Date.now();
            compression.totalDuration = compression.endTime - compression.startTime;
            compression.result = result;
            compression.finalMetrics = {
                memory: this.getMemoryMetrics(),
                performance: this.getPerformanceMetrics()
            };

            // Calculate compression efficiency
            this.calculateCompressionEfficiency(compression);
        }
    }

    /**
     * Calculate compression efficiency metrics
     */
    calculateCompressionEfficiency(compression) {
        const efficiency = {
            timePerMB: 0,
            compressionRatio: 0,
            memoryEfficiency: 0,
            overallRating: 'unknown'
        };

        if (compression.result.originalSize && compression.result.compressedSize) {
            const originalSizeMB = compression.result.originalSize / (1024 * 1024);
            efficiency.timePerMB = compression.totalDuration / originalSizeMB;
            efficiency.compressionRatio = 1 - (compression.result.compressedSize / compression.result.originalSize);
        }

        // Memory efficiency (lower is better)
        const initialMemory = compression.initialMetrics.memory.usageRatio;
        const finalMemory = compression.finalMetrics.memory.usageRatio;
        efficiency.memoryEfficiency = finalMemory - initialMemory;

        // Overall rating
        if (efficiency.compressionRatio > 0.5 && efficiency.timePerMB < 5000) {
            efficiency.overallRating = 'excellent';
        } else if (efficiency.compressionRatio > 0.3 && efficiency.timePerMB < 10000) {
            efficiency.overallRating = 'good';
        } else if (efficiency.compressionRatio > 0.1 && efficiency.timePerMB < 20000) {
            efficiency.overallRating = 'fair';
        } else {
            efficiency.overallRating = 'poor';
        }

        compression.efficiency = efficiency;
    }

    /**
     * Get performance recommendations for device
     */
    getPerformanceRecommendations() {
        const latestMetrics = this.metrics.performanceHistory[this.metrics.performanceHistory.length - 1];
        const recommendations = [];

        if (!latestMetrics) {
            return ['Performance data not available'];
        }

        // Memory recommendations
        if (latestMetrics.memory.available) {
            if (latestMetrics.memory.usageRatio > 0.8) {
                recommendations.push('Alto uso de memória - considere fechar outras abas');
            } else if (latestMetrics.memory.usageRatio > 0.6) {
                recommendations.push('Uso moderado de memória - compressão disponível com configurações conservadoras');
            } else {
                recommendations.push('Memória suficiente - todas as configurações de compressão disponíveis');
            }
        }

        // Network recommendations
        if (latestMetrics.network.available) {
            if (latestMetrics.network.effectiveType === '4g' || latestMetrics.network.downlink > 10) {
                recommendations.push('Rede rápida - compressão pode não ser necessária para arquivos pequenos');
            } else if (latestMetrics.network.effectiveType === '3g') {
                recommendations.push('Rede moderada - compressão recomendada para arquivos grandes');
            } else {
                recommendations.push('Rede lenta - compressão altamente recomendada');
            }
        }

        // Device performance recommendations
        const cpuCores = this.metrics.deviceMetrics.hardwareConcurrency;
        if (cpuCores >= 8) {
            recommendations.push('Dispositivo potente - compressão rápida disponível');
        } else if (cpuCores >= 4) {
            recommendations.push('Dispositivo moderado - compressão disponível');
        } else {
            recommendations.push('Dispositivo limitado - use configurações de compressão rápida');
        }

        return recommendations;
    }

    /**
     * Get compression statistics
     */
    getCompressionStats() {
        const completedCompressions = this.metrics.compressions.filter(c => c.completed);
        
        if (completedCompressions.length === 0) {
            return null;
        }

        const stats = {
            totalCompressions: completedCompressions.length,
            averageDuration: 0,
            averageCompressionRatio: 0,
            averageTimePerMB: 0,
            successRate: 0,
            ratingDistribution: {
                excellent: 0,
                good: 0,
                fair: 0,
                poor: 0
            }
        };

        let totalDuration = 0;
        let totalCompressionRatio = 0;
        let totalTimePerMB = 0;
        let successfulCompressions = 0;

        completedCompressions.forEach(compression => {
            totalDuration += compression.totalDuration;

            if (compression.efficiency) {
                totalCompressionRatio += compression.efficiency.compressionRatio;
                totalTimePerMB += compression.efficiency.timePerMB;
                stats.ratingDistribution[compression.efficiency.overallRating]++;
                successfulCompressions++;
            }
        });

        stats.averageDuration = totalDuration / completedCompressions.length;
        stats.successRate = successfulCompressions / completedCompressions.length;

        if (successfulCompressions > 0) {
            stats.averageCompressionRatio = totalCompressionRatio / successfulCompressions;
            stats.averageTimePerMB = totalTimePerMB / successfulCompressions;
        }

        return stats;
    }

    /**
     * Export performance data for analysis
     */
    exportPerformanceData() {
        return {
            deviceMetrics: this.metrics.deviceMetrics,
            performanceHistory: this.metrics.performanceHistory,
            compressions: this.metrics.compressions.map(c => ({
                id: c.id,
                duration: c.totalDuration,
                efficiency: c.efficiency,
                options: c.options,
                stages: c.stages.length
            })),
            stats: this.getCompressionStats(),
            recommendations: this.getPerformanceRecommendations()
        };
    }

    /**
     * Detect mobile device
     */
    detectMobileDevice() {
        const userAgent = navigator.userAgent.toLowerCase();
        const mobileKeywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'];
        
        // Check user agent
        const isMobileUA = mobileKeywords.some(keyword => userAgent.includes(keyword));
        
        // Check touch capabilities
        const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        // Check screen size
        const isSmallScreen = window.screen.width <= 768 || window.screen.height <= 768;
        
        // Check device memory (mobile devices typically have less)
        const hasLimitedMemory = navigator.deviceMemory && navigator.deviceMemory <= 4;
        
        return isMobileUA || (hasTouch && isSmallScreen) || hasLimitedMemory;
    }

    /**
     * Setup mobile-specific optimizations
     */
    setupMobileOptimizations() {
        if (!this.isMobileDevice) return;

        // Adjust thresholds for mobile
        this.thresholds.memoryUsage = this.thresholds.mobileMemoryUsage;
        this.thresholds.batteryLevel = this.thresholds.mobileBatteryLevel;
        this.thresholds.maxCompressions = 1; // Only one compression at a time on mobile

        // Setup battery monitoring
        this.setupBatteryMonitoring();

        // Setup thermal monitoring
        this.setupThermalMonitoring();

        // Setup page lifecycle monitoring
        this.setupPageLifecycleMonitoring();

        // Setup network change monitoring
        this.setupNetworkChangeMonitoring();

        console.log('Mobile optimizations enabled');
    }

    /**
     * Setup battery monitoring for mobile devices
     */
    async setupBatteryMonitoring() {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                this.batteryMonitoring = true;

                // Monitor battery level changes
                battery.addEventListener('levelchange', () => {
                    this.handleBatteryChange(battery);
                });

                // Monitor charging state changes
                battery.addEventListener('chargingchange', () => {
                    this.handleBatteryChange(battery);
                });

                // Initial check
                this.handleBatteryChange(battery);
            }
        } catch (error) {
            console.warn('Battery monitoring setup failed:', error);
        }
    }

    /**
     * Handle battery level changes
     */
    handleBatteryChange(battery) {
        const batteryInfo = {
            level: battery.level,
            charging: battery.charging,
            timestamp: Date.now()
        };

        // Update metrics
        this.metrics.mobileOptimizations.lastBatteryUpdate = batteryInfo;

        // Check if battery is critically low
        if (!battery.charging && battery.level < this.thresholds.batteryLevel) {
            this.triggerLowBatteryMode();
        } else if (battery.charging || battery.level > this.thresholds.batteryLevel + 0.1) {
            this.exitLowBatteryMode();
        }
    }

    /**
     * Trigger low battery mode
     */
    triggerLowBatteryMode() {
        this.metrics.mobileOptimizations.lowBatteryMode = true;
        
        // Emit event for UI to handle
        window.dispatchEvent(new CustomEvent('compression-low-battery', {
            detail: {
                batteryLevel: this.metrics.mobileOptimizations.lastBatteryUpdate?.level,
                recommendation: 'Considere conectar o carregador antes de continuar'
            }
        }));

        console.warn('Low battery mode activated');
    }

    /**
     * Exit low battery mode
     */
    exitLowBatteryMode() {
        if (this.metrics.mobileOptimizations.lowBatteryMode) {
            this.metrics.mobileOptimizations.lowBatteryMode = false;
            
            window.dispatchEvent(new CustomEvent('compression-battery-ok', {
                detail: {
                    batteryLevel: this.metrics.mobileOptimizations.lastBatteryUpdate?.level
                }
            }));

            console.log('Low battery mode deactivated');
        }
    }

    /**
     * Setup thermal monitoring
     */
    setupThermalMonitoring() {
        // Monitor for performance degradation that might indicate thermal throttling
        this.thermalMonitoring = true;
        this.thermalCheckInterval = setInterval(() => {
            this.checkThermalState();
        }, 15000); // Check every 15 seconds
    }

    /**
     * Check thermal state through performance indicators
     */
    checkThermalState() {
        // Measure performance timing variations
        const startTime = performance.now();
        
        // Simple computational task to test performance
        let sum = 0;
        for (let i = 0; i < 100000; i++) {
            sum += Math.random();
        }
        
        const endTime = performance.now();
        const computationTime = endTime - startTime;

        // Store computation time history
        if (!this.metrics.mobileOptimizations.computationHistory) {
            this.metrics.mobileOptimizations.computationHistory = [];
        }

        this.metrics.mobileOptimizations.computationHistory.push({
            time: computationTime,
            timestamp: Date.now()
        });

        // Keep only last 10 measurements
        if (this.metrics.mobileOptimizations.computationHistory.length > 10) {
            this.metrics.mobileOptimizations.computationHistory.shift();
        }

        // Check for thermal throttling
        if (this.metrics.mobileOptimizations.computationHistory.length >= 5) {
            const recent = this.metrics.mobileOptimizations.computationHistory.slice(-3);
            const older = this.metrics.mobileOptimizations.computationHistory.slice(0, 3);
            
            const recentAvg = recent.reduce((sum, item) => sum + item.time, 0) / recent.length;
            const olderAvg = older.reduce((sum, item) => sum + item.time, 0) / older.length;
            
            // If computation time increased by more than 50%, likely thermal throttling
            if (recentAvg > olderAvg * 1.5) {
                this.handleThermalThrottling();
            }
        }
    }

    /**
     * Handle thermal throttling detection
     */
    handleThermalThrottling() {
        this.metrics.mobileOptimizations.thermalThrottling = true;
        
        window.dispatchEvent(new CustomEvent('compression-thermal-throttling', {
            detail: {
                recommendation: 'Dispositivo aquecido. Recomendamos pausar a compressão.'
            }
        }));

        console.warn('Thermal throttling detected');
    }

    /**
     * Setup page lifecycle monitoring for mobile
     */
    setupPageLifecycleMonitoring() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handlePageHidden();
            } else {
                this.handlePageVisible();
            }
        });

        // Handle page freeze/resume (modern browsers)
        document.addEventListener('freeze', () => {
            this.handlePageFreeze();
        });

        document.addEventListener('resume', () => {
            this.handlePageResume();
        });
    }

    /**
     * Handle page becoming hidden
     */
    handlePageHidden() {
        this.metrics.mobileOptimizations.pageHidden = true;
        this.metrics.mobileOptimizations.pageHiddenTime = Date.now();
        
        // Emit event to pause compressions
        window.dispatchEvent(new CustomEvent('compression-page-hidden'));
    }

    /**
     * Handle page becoming visible
     */
    handlePageVisible() {
        if (this.metrics.mobileOptimizations.pageHidden) {
            this.metrics.mobileOptimizations.pageHidden = false;
            const hiddenDuration = Date.now() - this.metrics.mobileOptimizations.pageHiddenTime;
            
            // If page was hidden for more than 30 seconds, check if compression should resume
            if (hiddenDuration > 30000) {
                window.dispatchEvent(new CustomEvent('compression-page-visible-long', {
                    detail: { hiddenDuration }
                }));
            } else {
                window.dispatchEvent(new CustomEvent('compression-page-visible'));
            }
        }
    }

    /**
     * Handle page freeze
     */
    handlePageFreeze() {
        this.metrics.mobileOptimizations.pageFrozen = true;
        window.dispatchEvent(new CustomEvent('compression-page-freeze'));
    }

    /**
     * Handle page resume
     */
    handlePageResume() {
        this.metrics.mobileOptimizations.pageFrozen = false;
        window.dispatchEvent(new CustomEvent('compression-page-resume'));
    }

    /**
     * Setup network change monitoring
     */
    setupNetworkChangeMonitoring() {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        
        if (connection) {
            connection.addEventListener('change', () => {
                this.handleNetworkChange();
            });
        }
    }

    /**
     * Handle network connection changes
     */
    handleNetworkChange() {
        const networkInfo = this.getConnectionInfo();
        this.metrics.mobileOptimizations.lastNetworkChange = {
            ...networkInfo,
            timestamp: Date.now()
        };

        // Check if network became significantly slower
        if (networkInfo.available) {
            if (networkInfo.effectiveType === 'slow-2g' || networkInfo.effectiveType === '2g') {
                window.dispatchEvent(new CustomEvent('compression-network-slow', {
                    detail: {
                        networkType: networkInfo.effectiveType,
                        downlink: networkInfo.downlink
                    }
                }));
            } else if (networkInfo.effectiveType === '4g' || networkInfo.downlink > 10) {
                window.dispatchEvent(new CustomEvent('compression-network-fast', {
                    detail: {
                        networkType: networkInfo.effectiveType,
                        downlink: networkInfo.downlink
                    }
                }));
            }
        }
    }

    /**
     * Get mobile-specific performance recommendations
     */
    getMobilePerformanceRecommendations() {
        if (!this.isMobileDevice) {
            return this.getPerformanceRecommendations();
        }

        const recommendations = [];
        const mobileOpts = this.metrics.mobileOptimizations;

        // Battery recommendations
        if (mobileOpts.lowBatteryMode) {
            recommendations.push('⚠️ Bateria baixa - conecte o carregador antes de continuar');
        } else if (mobileOpts.lastBatteryUpdate && !mobileOpts.lastBatteryUpdate.charging) {
            recommendations.push('🔋 Considere conectar o carregador para compressões longas');
        }

        // Thermal recommendations
        if (mobileOpts.thermalThrottling) {
            recommendations.push('🌡️ Dispositivo aquecido - aguarde esfriar ou use envio direto');
        }

        // Network recommendations
        if (mobileOpts.lastNetworkChange) {
            const network = mobileOpts.lastNetworkChange;
            if (network.effectiveType === 'slow-2g' || network.effectiveType === '2g') {
                recommendations.push('📶 Rede lenta - compressão altamente recomendada');
            } else if (network.effectiveType === '4g' && network.downlink > 10) {
                recommendations.push('📶 Rede rápida - compressão opcional para arquivos pequenos');
            }
        }

        // Page visibility recommendations
        if (mobileOpts.pageHidden) {
            recommendations.push('👁️ Mantenha a página ativa durante a compressão');
        }

        // Memory recommendations for mobile
        const latestMetrics = this.metrics.performanceHistory[this.metrics.performanceHistory.length - 1];
        if (latestMetrics && latestMetrics.memory.available) {
            if (latestMetrics.memory.usageRatio > 0.7) {
                recommendations.push('💾 Alto uso de memória - use configurações rápidas ou envio direto');
            }
        }

        // General mobile recommendations
        recommendations.push('📱 Para melhor performance: feche outras abas e aplicativos');

        return recommendations;
    }

    /**
     * Check if compression should be allowed on mobile
     */
    shouldAllowCompressionOnMobile() {
        if (!this.isMobileDevice) return true;

        const mobileOpts = this.metrics.mobileOptimizations;

        // Block if battery is critically low
        if (mobileOpts.lowBatteryMode) {
            return { allowed: false, reason: 'low_battery' };
        }

        // Block if thermal throttling is detected
        if (mobileOpts.thermalThrottling) {
            return { allowed: false, reason: 'thermal_throttling' };
        }

        // Block if page is frozen
        if (mobileOpts.pageFrozen) {
            return { allowed: false, reason: 'page_frozen' };
        }

        // Warn if page is hidden
        if (mobileOpts.pageHidden) {
            return { allowed: true, warning: 'page_hidden' };
        }

        return { allowed: true };
    }

    /**
     * Get optimized compression settings for mobile
     */
    getMobileOptimizedSettings() {
        if (!this.isMobileDevice) return null;

        const settings = {
            preset: 'mobile-optimized',
            maxDuration: 30000, // 30 seconds max
            chunkSize: 16 * 1024 * 1024, // 16MB chunks
            quality: 'balanced'
        };

        const mobileOpts = this.metrics.mobileOptimizations;

        // Adjust settings based on current conditions
        if (mobileOpts.thermalThrottling) {
            settings.preset = 'mobile-fast';
            settings.maxDuration = 15000;
            settings.quality = 'speed';
        }

        if (mobileOpts.lowBatteryMode) {
            settings.preset = 'mobile-fast';
            settings.maxDuration = 10000;
            settings.quality = 'speed';
        }

        // Adjust based on network conditions
        if (mobileOpts.lastNetworkChange) {
            const network = mobileOpts.lastNetworkChange;
            if (network.effectiveType === 'slow-2g' || network.effectiveType === '2g') {
                settings.quality = 'high_compression';
            } else if (network.effectiveType === '4g' && network.downlink > 10) {
                settings.quality = 'balanced';
            }
        }

        return settings;
    }

    /**
     * Clean up mobile monitoring
     */
    cleanup() {
        this.clearHistory();
        
        if (this.thermalCheckInterval) {
            clearInterval(this.thermalCheckInterval);
        }
        
        // Clean up event listeners would be here in a full implementation
        console.log('Mobile performance monitoring cleaned up');
    }

    /**
     * Clear performance history
     */
    clearHistory() {
        this.metrics.performanceHistory = [];
        this.metrics.compressions = [];
        this.metrics.mobileOptimizations = {};
    }
}

// Export for use in other modules
window.CompressionPerformanceMonitor = CompressionPerformanceMonitor;