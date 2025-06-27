/**
 * CompressionMonitoring - Comprehensive monitoring and analytics for video compression
 * Part of Phase 3: Production Deployment & Monitoring
 */

class CompressionMonitoring {
    constructor() {
        this.metrics = {
            compressions: new Map(),
            errors: [],
            performance: [],
            userSessions: new Map(),
            deviceMetrics: {},
            networkMetrics: []
        };
        
        this.config = {
            maxMetricsHistory: 1000,
            maxErrorHistory: 500,
            batchSize: 50,
            flushInterval: 60000, // 1 minute
            emergencyFlushThreshold: 100
        };
        
        this.monitoring = true;
        this.flushTimer = null;
        
        this.initializeMonitoring();
    }

    /**
     * Initialize monitoring system
     */
    initializeMonitoring() {
        // Collect initial device metrics
        this.collectDeviceMetrics();
        
        // Setup periodic flushing
        this.setupPeriodicFlush();
        
        // Setup global error handling
        this.setupGlobalErrorHandling();
        
        // Setup performance monitoring
        this.setupPerformanceMonitoring();
        
        // Setup user session tracking
        this.startUserSession();
        
        console.log('Compression monitoring initialized');
    }

    /**
     * Start tracking a compression operation
     */
    startCompressionTracking(compressionId, options = {}) {
        const compression = {
            id: compressionId,
            startTime: Date.now(),
            endTime: null,
            status: 'started',
            options: { ...options },
            stages: [],
            errors: [],
            performance: {
                fileSize: options.fileSize || 0,
                estimatedDuration: null,
                actualDuration: null,
                compressionRatio: null,
                processingSpeed: null
            },
            device: {
                userAgent: navigator.userAgent,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                isMobile: this.isMobileDevice()
            },
            network: this.getCurrentNetworkInfo(),
            medicalContext: options.medicalContext || null
        };

        this.metrics.compressions.set(compressionId, compression);
        
        // Track compression start event
        this.trackEvent('compression_started', {
            compressionId,
            fileSize: options.fileSize,
            preset: options.preset,
            medicalPriority: options.medicalContext?.priority
        });
        
        return compression;
    }

    /**
     * Update compression stage
     */
    updateCompressionStage(compressionId, stage, progress = 0, data = {}) {
        const compression = this.metrics.compressions.get(compressionId);
        
        if (!compression) {
            console.warn('Compression not found:', compressionId);
            return;
        }

        const stageInfo = {
            stage,
            progress,
            timestamp: Date.now(),
            duration: Date.now() - compression.startTime,
            memoryUsage: this.getCurrentMemoryUsage(),
            ...data
        };

        compression.stages.push(stageInfo);
        compression.status = stage;
        
        // Track stage progress
        this.trackEvent('compression_stage', {
            compressionId,
            stage,
            progress,
            duration: stageInfo.duration
        });
    }

    /**
     * Complete compression tracking
     */
    completeCompressionTracking(compressionId, result = {}) {
        const compression = this.metrics.compressions.get(compressionId);
        
        if (!compression) {
            console.warn('Compression not found:', compressionId);
            return;
        }

        compression.endTime = Date.now();
        compression.performance.actualDuration = compression.endTime - compression.startTime;
        compression.status = result.success ? 'completed' : 'failed';
        
        // Calculate performance metrics
        if (result.success && result.compressedSize) {
            compression.performance.compressionRatio = 
                1 - (result.compressedSize / compression.performance.fileSize);
            compression.performance.processingSpeed = 
                compression.performance.fileSize / compression.performance.actualDuration; // bytes per ms
        }
        
        // Track completion
        this.trackEvent('compression_completed', {
            compressionId,
            success: result.success,
            duration: compression.performance.actualDuration,
            compressionRatio: compression.performance.compressionRatio,
            error: result.error
        });
        
        // Calculate user experience metrics
        this.calculateUserExperienceMetrics(compression);
        
        return compression;
    }

    /**
     * Track compression error
     */
    trackCompressionError(compressionId, error, context = {}) {
        const errorInfo = {
            compressionId,
            error: {
                message: error.message,
                stack: error.stack,
                name: error.name
            },
            context,
            timestamp: Date.now(),
            device: {
                userAgent: navigator.userAgent,
                isMobile: this.isMobileDevice(),
                memory: this.getCurrentMemoryUsage()
            },
            network: this.getCurrentNetworkInfo(),
            recovery: null
        };

        this.metrics.errors.push(errorInfo);
        
        // Update compression record
        const compression = this.metrics.compressions.get(compressionId);
        if (compression) {
            compression.errors.push(errorInfo);
            compression.status = 'error';
        }
        
        // Track error event
        this.trackEvent('compression_error', {
            compressionId,
            errorType: error.name,
            errorMessage: error.message,
            context
        });
        
        // Emergency flush if too many errors
        if (this.metrics.errors.length >= this.config.emergencyFlushThreshold) {
            this.flushMetrics(true);
        }
    }

    /**
     * Track error recovery
     */
    trackErrorRecovery(compressionId, recovery) {
        const compression = this.metrics.compressions.get(compressionId);
        
        if (compression && compression.errors.length > 0) {
            const lastError = compression.errors[compression.errors.length - 1];
            lastError.recovery = {
                strategy: recovery.strategy,
                successful: recovery.successful,
                timestamp: Date.now()
            };
        }
        
        this.trackEvent('error_recovery', {
            compressionId,
            strategy: recovery.strategy,
            successful: recovery.successful
        });
    }

    /**
     * Track user interaction
     */
    trackUserInteraction(action, data = {}) {
        this.trackEvent('user_interaction', {
            action,
            timestamp: Date.now(),
            ...data
        });
    }

    /**
     * Track performance metrics
     */
    trackPerformanceMetric(metric, value, context = {}) {
        const performanceEntry = {
            metric,
            value,
            timestamp: Date.now(),
            context,
            device: {
                isMobile: this.isMobileDevice(),
                memory: this.getCurrentMemoryUsage()
            }
        };

        this.metrics.performance.push(performanceEntry);
        
        // Keep only recent entries
        if (this.metrics.performance.length > this.config.maxMetricsHistory) {
            this.metrics.performance.shift();
        }
    }

    /**
     * Track network quality changes
     */
    trackNetworkChange(networkInfo) {
        const networkEntry = {
            ...networkInfo,
            timestamp: Date.now()
        };

        this.metrics.networkMetrics.push(networkEntry);
        
        this.trackEvent('network_change', networkInfo);
    }

    /**
     * Generic event tracking
     */
    trackEvent(eventType, data = {}) {
        const event = {
            type: eventType,
            data,
            timestamp: Date.now(),
            sessionId: this.getSessionId(),
            userId: this.getUserId()
        };

        // Add to batch for sending
        this.addToBatch(event);
    }

    /**
     * Calculate user experience metrics
     */
    calculateUserExperienceMetrics(compression) {
        const metrics = {
            timeToFirstProgress: null,
            timeToCompletion: compression.performance.actualDuration,
            stageCount: compression.stages.length,
            errorCount: compression.errors.length,
            userSatisfaction: null
        };

        // Time to first progress
        if (compression.stages.length > 0) {
            metrics.timeToFirstProgress = compression.stages[0].timestamp - compression.startTime;
        }

        // Calculate user satisfaction score (0-100)
        let satisfactionScore = 100;
        
        // Deduct points for long duration (medical context matters)
        const expectedDuration = this.getExpectedDuration(compression.performance.fileSize);
        if (compression.performance.actualDuration > expectedDuration * 1.5) {
            satisfactionScore -= 20;
        }
        
        // Deduct points for errors
        satisfactionScore -= compression.errors.length * 15;
        
        // Bonus points for good compression ratio
        if (compression.performance.compressionRatio > 0.5) {
            satisfactionScore += 10;
        }
        
        // Medical context adjustments
        if (compression.medicalContext?.priority === 'emergency') {
            // Emergency cases: speed is more important than compression
            if (compression.performance.actualDuration < 15000) { // Less than 15 seconds
                satisfactionScore += 15;
            }
        }
        
        metrics.userSatisfaction = Math.max(0, Math.min(100, satisfactionScore));
        
        compression.userExperience = metrics;
        
        this.trackEvent('user_experience_calculated', {
            compressionId: compression.id,
            ...metrics
        });
    }

    /**
     * Get expected compression duration based on file size
     */
    getExpectedDuration(fileSize) {
        // Rough estimation: 1MB per 2 seconds on average device
        return (fileSize / (1024 * 1024)) * 2000;
    }

    /**
     * Setup global error handling
     */
    setupGlobalErrorHandling() {
        // Catch unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.trackGlobalError(event.reason, 'unhandled_promise_rejection');
        });

        // Catch general JavaScript errors
        window.addEventListener('error', (event) => {
            // Only track compression-related errors
            if (event.filename && event.filename.includes('compression')) {
                this.trackGlobalError(event.error || new Error(event.message), 'javascript_error');
            }
        });
    }

    /**
     * Track global errors
     */
    trackGlobalError(error, type) {
        const errorInfo = {
            type,
            error: {
                message: error.message,
                stack: error.stack,
                name: error.name
            },
            timestamp: Date.now(),
            url: window.location.href,
            device: {
                userAgent: navigator.userAgent,
                isMobile: this.isMobileDevice()
            }
        };

        this.metrics.errors.push(errorInfo);
        
        this.trackEvent('global_error', {
            errorType: type,
            errorMessage: error.message
        });
    }

    /**
     * Setup performance monitoring
     */
    setupPerformanceMonitoring() {
        // Monitor page performance
        if ('performance' in window) {
            // Track initial page load metrics
            window.addEventListener('load', () => {
                setTimeout(() => {
                    this.collectPagePerformanceMetrics();
                }, 1000);
            });
        }

        // Monitor memory usage periodically
        setInterval(() => {
            this.trackPerformanceMetric('memory_usage', this.getCurrentMemoryUsage());
        }, 30000); // Every 30 seconds
    }

    /**
     * Collect page performance metrics
     */
    collectPagePerformanceMetrics() {
        if (!performance.timing) return;

        const timing = performance.timing;
        const metrics = {
            pageLoadTime: timing.loadEventEnd - timing.navigationStart,
            domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
            firstPaint: this.getFirstPaintTime(),
            resourceLoadTime: timing.loadEventEnd - timing.domContentLoadedEventEnd
        };

        this.trackEvent('page_performance', metrics);
    }

    /**
     * Get first paint time
     */
    getFirstPaintTime() {
        try {
            const paintEntries = performance.getEntriesByType('paint');
            const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
            return firstPaint ? firstPaint.startTime : null;
        } catch (error) {
            return null;
        }
    }

    /**
     * Start user session tracking
     */
    startUserSession() {
        const sessionId = this.getSessionId();
        const session = {
            id: sessionId,
            startTime: Date.now(),
            endTime: null,
            compressions: [],
            interactions: [],
            device: this.metrics.deviceMetrics,
            network: this.getCurrentNetworkInfo()
        };

        this.metrics.userSessions.set(sessionId, session);
        
        this.trackEvent('session_started', {
            sessionId,
            device: session.device,
            network: session.network
        });

        // Track session end
        window.addEventListener('beforeunload', () => {
            this.endUserSession();
        });
    }

    /**
     * End user session
     */
    endUserSession() {
        const sessionId = this.getSessionId();
        const session = this.metrics.userSessions.get(sessionId);
        
        if (session) {
            session.endTime = Date.now();
            session.duration = session.endTime - session.startTime;
            
            this.trackEvent('session_ended', {
                sessionId,
                duration: session.duration,
                compressionCount: session.compressions.length
            });
        }
        
        // Flush remaining metrics
        this.flushMetrics(true);
    }

    /**
     * Collect device metrics
     */
    collectDeviceMetrics() {
        this.metrics.deviceMetrics = {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            hardwareConcurrency: navigator.hardwareConcurrency,
            deviceMemory: navigator.deviceMemory,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screenResolution: `${screen.width}x${screen.height}`,
            colorDepth: screen.colorDepth,
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timestamp: Date.now()
        };

        // Collect battery info if available
        this.collectBatteryInfo();
    }

    /**
     * Collect battery information
     */
    async collectBatteryInfo() {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                this.metrics.deviceMetrics.battery = {
                    level: battery.level,
                    charging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime
                };
            }
        } catch (error) {
            // Battery API not available
        }
    }

    /**
     * Get current memory usage
     */
    getCurrentMemoryUsage() {
        if ('memory' in performance) {
            const memory = performance.memory;
            return {
                usedJSHeapSize: memory.usedJSHeapSize,
                totalJSHeapSize: memory.totalJSHeapSize,
                jsHeapSizeLimit: memory.jsHeapSizeLimit,
                usageRatio: memory.usedJSHeapSize / memory.jsHeapSizeLimit
            };
        }
        return null;
    }

    /**
     * Get current network information
     */
    getCurrentNetworkInfo() {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        
        if (connection) {
            return {
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
     * Detect if device is mobile
     */
    isMobileDevice() {
        const userAgent = navigator.userAgent.toLowerCase();
        return /mobile|android|iphone|ipad|ipod/.test(userAgent) || 
               ('ontouchstart' in window && window.screen.width <= 768);
    }

    /**
     * Get session ID
     */
    getSessionId() {
        let sessionId = sessionStorage.getItem('compression_session_id');
        
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('compression_session_id', sessionId);
        }
        
        return sessionId;
    }

    /**
     * Get user ID
     */
    getUserId() {
        let userId = localStorage.getItem('compression_user_id');
        
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('compression_user_id', userId);
        }
        
        return userId;
    }

    /**
     * Add event to batch for sending
     */
    addToBatch(event) {
        if (!this.batchedEvents) {
            this.batchedEvents = [];
        }
        
        this.batchedEvents.push(event);
        
        // Emergency flush if batch gets too large
        if (this.batchedEvents.length >= this.config.emergencyFlushThreshold) {
            this.flushMetrics(true);
        }
    }

    /**
     * Setup periodic metric flushing
     */
    setupPeriodicFlush() {
        this.flushTimer = setInterval(() => {
            this.flushMetrics();
        }, this.config.flushInterval);
    }

    /**
     * Flush metrics to server
     */
    async flushMetrics(immediate = false) {
        if (!this.batchedEvents || this.batchedEvents.length === 0) return;

        const payload = {
            sessionId: this.getSessionId(),
            userId: this.getUserId(),
            events: this.batchedEvents.splice(0, this.config.batchSize),
            deviceMetrics: this.metrics.deviceMetrics,
            timestamp: Date.now()
        };

        try {
            if (immediate && 'sendBeacon' in navigator) {
                // Use sendBeacon for immediate sending (e.g., on page unload)
                const success = navigator.sendBeacon(
                    '/api/compression-monitoring/', 
                    JSON.stringify(payload)
                );
                
                if (success) {
                    console.log('Metrics flushed via beacon:', payload.events.length, 'events');
                }
            } else {
                // Use fetch for regular sending
                const response = await fetch('/api/compression-monitoring/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    console.log('Metrics flushed:', payload.events.length, 'events');
                } else {
                    console.warn('Failed to flush metrics:', response.status);
                    // Put events back in queue for retry
                    this.batchedEvents.unshift(...payload.events);
                }
            }
        } catch (error) {
            console.warn('Error flushing metrics:', error);
            // Put events back in queue for retry
            this.batchedEvents.unshift(...payload.events);
        }
    }

    /**
     * Get CSRF token for Django
     */
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    /**
     * Get monitoring statistics
     */
    getStatistics() {
        const stats = {
            compressions: {
                total: this.metrics.compressions.size,
                completed: 0,
                failed: 0,
                inProgress: 0
            },
            errors: {
                total: this.metrics.errors.length,
                byType: {}
            },
            performance: {
                averageDuration: 0,
                averageCompressionRatio: 0,
                averageUserSatisfaction: 0
            },
            device: this.metrics.deviceMetrics,
            network: this.getCurrentNetworkInfo()
        };

        // Calculate compression statistics
        let totalDuration = 0;
        let totalCompressionRatio = 0;
        let totalUserSatisfaction = 0;
        let completedCount = 0;

        this.metrics.compressions.forEach(compression => {
            switch (compression.status) {
                case 'completed':
                    stats.compressions.completed++;
                    if (compression.performance.actualDuration) {
                        totalDuration += compression.performance.actualDuration;
                        completedCount++;
                    }
                    if (compression.performance.compressionRatio) {
                        totalCompressionRatio += compression.performance.compressionRatio;
                    }
                    if (compression.userExperience?.userSatisfaction) {
                        totalUserSatisfaction += compression.userExperience.userSatisfaction;
                    }
                    break;
                case 'failed':
                case 'error':
                    stats.compressions.failed++;
                    break;
                default:
                    stats.compressions.inProgress++;
            }
        });

        // Calculate averages
        if (completedCount > 0) {
            stats.performance.averageDuration = totalDuration / completedCount;
            stats.performance.averageCompressionRatio = totalCompressionRatio / completedCount;
            stats.performance.averageUserSatisfaction = totalUserSatisfaction / completedCount;
        }

        // Count errors by type
        this.metrics.errors.forEach(error => {
            const type = error.error?.name || 'Unknown';
            stats.errors.byType[type] = (stats.errors.byType[type] || 0) + 1;
        });

        return stats;
    }

    /**
     * Get detailed metrics for debugging
     */
    getDetailedMetrics() {
        return {
            compressions: Array.from(this.metrics.compressions.values()),
            errors: this.metrics.errors,
            performance: this.metrics.performance,
            userSessions: Array.from(this.metrics.userSessions.values()),
            deviceMetrics: this.metrics.deviceMetrics,
            networkMetrics: this.metrics.networkMetrics,
            statistics: this.getStatistics()
        };
    }

    /**
     * Clean up monitoring
     */
    cleanup() {
        this.monitoring = false;
        
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
        }
        
        // Final flush
        this.flushMetrics(true);
        
        console.log('Compression monitoring cleaned up');
    }
}

// Export for use in other modules
window.CompressionMonitoring = CompressionMonitoring;