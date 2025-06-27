/**
 * FeatureFlags - Feature flag system for video compression
 * Part of Phase 3: Production Deployment & Monitoring
 */

class CompressionFeatureFlags {
    constructor() {
        this.flags = new Map();
        this.userSegments = new Set();
        this.experiments = new Map();
        this.analytics = [];
        
        this.initializeDefaultFlags();
        this.loadUserSegments();
        this.setupAnalytics();
    }

    /**
     * Initialize default feature flags
     */
    initializeDefaultFlags() {
        // Core compression features
        this.flags.set('compression_enabled', {
            enabled: true,
            rolloutPercentage: 100,
            segments: ['all'],
            conditions: {
                minBrowserVersion: { chrome: 80, firefox: 75, safari: 13 },
                deviceTypes: ['desktop', 'mobile', 'tablet'],
                excludeUserAgents: []
            },
            lastUpdated: Date.now()
        });

        // Advanced compression features
        this.flags.set('advanced_compression', {
            enabled: true,
            rolloutPercentage: 80,
            segments: ['beta_testers', 'power_users'],
            conditions: {
                minMemory: 4, // GB
                minCpuCores: 4,
                excludeLowEndDevices: true
            },
            lastUpdated: Date.now()
        });

        // Mobile optimizations
        this.flags.set('mobile_optimizations', {
            enabled: true,
            rolloutPercentage: 100,
            segments: ['mobile_users'],
            conditions: {
                deviceTypes: ['mobile'],
                minBatteryLevel: 0.2,
                allowThermalThrottling: false
            },
            lastUpdated: Date.now()
        });

        // Emergency bypass
        this.flags.set('emergency_bypass', {
            enabled: true,
            rolloutPercentage: 100,
            segments: ['all'],
            conditions: {
                medicalContext: ['emergency', 'urgent']
            },
            lastUpdated: Date.now()
        });

        // Experimental features
        this.flags.set('experimental_codecs', {
            enabled: false,
            rolloutPercentage: 5,
            segments: ['beta_testers'],
            conditions: {
                browserSupport: ['chrome', 'edge'],
                minVersion: { chrome: 90, edge: 90 }
            },
            lastUpdated: Date.now()
        });

        // A/B testing flags
        this.flags.set('compression_ui_v2', {
            enabled: false,
            rolloutPercentage: 50,
            segments: ['ab_test_group_a'],
            abTest: {
                name: 'compression_ui_test',
                variants: ['v1', 'v2'],
                allocation: { v1: 50, v2: 50 }
            },
            lastUpdated: Date.now()
        });
    }

    /**
     * Load user segments from server or local storage
     */
    loadUserSegments() {
        // In a real implementation, this would load from server
        // For now, determine segments based on device characteristics
        
        // Add basic segments
        this.userSegments.add('all');
        
        // Device-based segments
        if (this.isMobileDevice()) {
            this.userSegments.add('mobile_users');
        } else {
            this.userSegments.add('desktop_users');
        }
        
        // Performance-based segments
        if (this.isHighEndDevice()) {
            this.userSegments.add('power_users');
        } else if (this.isLowEndDevice()) {
            this.userSegments.add('limited_users');
        }
        
        // Beta tester detection (could be based on user account, URL params, etc.)
        if (this.isBetaTester()) {
            this.userSegments.add('beta_testers');
        }
        
        // A/B test group assignment
        this.assignABTestGroups();
        
        console.log('User segments:', Array.from(this.userSegments));
    }

    /**
     * Setup analytics tracking
     */
    setupAnalytics() {
        // Track feature flag evaluations
        this.analyticsEnabled = true;
        
        // Send analytics periodically
        setInterval(() => {
            this.sendAnalytics();
        }, 300000); // Every 5 minutes
        
        // Send analytics on page unload
        window.addEventListener('beforeunload', () => {
            this.sendAnalytics(true);
        });
    }

    /**
     * Check if a feature flag is enabled for current user
     */
    isEnabled(flagName, context = {}) {
        const flag = this.flags.get(flagName);
        
        if (!flag) {
            this.logFlagEvaluation(flagName, false, 'flag_not_found');
            return false;
        }

        // Check if flag is globally disabled
        if (!flag.enabled) {
            this.logFlagEvaluation(flagName, false, 'globally_disabled');
            return false;
        }

        // Check rollout percentage
        if (!this.checkRolloutPercentage(flagName, flag.rolloutPercentage)) {
            this.logFlagEvaluation(flagName, false, 'rollout_percentage');
            return false;
        }

        // Check user segments
        if (!this.checkUserSegments(flag.segments)) {
            this.logFlagEvaluation(flagName, false, 'user_segments');
            return false;
        }

        // Check conditions
        if (!this.checkConditions(flag.conditions, context)) {
            this.logFlagEvaluation(flagName, false, 'conditions_not_met');
            return false;
        }

        this.logFlagEvaluation(flagName, true, 'enabled');
        return true;
    }

    /**
     * Get feature flag variant for A/B testing
     */
    getVariant(flagName, context = {}) {
        const flag = this.flags.get(flagName);
        
        if (!flag || !flag.abTest) {
            return null;
        }

        if (!this.isEnabled(flagName, context)) {
            return null;
        }

        // Determine variant based on user ID or device fingerprint
        const userId = this.getUserId();
        const hash = this.hashString(userId + flagName);
        const percentage = hash % 100;
        
        let cumulativePercentage = 0;
        for (const [variant, allocation] of Object.entries(flag.abTest.allocation)) {
            cumulativePercentage += allocation;
            if (percentage < cumulativePercentage) {
                this.logVariantAssignment(flagName, variant);
                return variant;
            }
        }
        
        return null;
    }

    /**
     * Check rollout percentage
     */
    checkRolloutPercentage(flagName, percentage) {
        if (percentage >= 100) return true;
        
        const userId = this.getUserId();
        const hash = this.hashString(userId + flagName);
        return (hash % 100) < percentage;
    }

    /**
     * Check if user is in required segments
     */
    checkUserSegments(requiredSegments) {
        if (!requiredSegments || requiredSegments.length === 0) return true;
        
        return requiredSegments.some(segment => 
            this.userSegments.has(segment) || segment === 'all'
        );
    }

    /**
     * Check feature flag conditions
     */
    checkConditions(conditions, context) {
        if (!conditions) return true;

        // Browser version check
        if (conditions.minBrowserVersion) {
            if (!this.checkBrowserVersion(conditions.minBrowserVersion)) {
                return false;
            }
        }

        // Device type check
        if (conditions.deviceTypes) {
            if (!this.checkDeviceType(conditions.deviceTypes)) {
                return false;
            }
        }

        // Memory check
        if (conditions.minMemory) {
            if (!this.checkMinMemory(conditions.minMemory)) {
                return false;
            }
        }

        // CPU cores check
        if (conditions.minCpuCores) {
            if (!this.checkMinCpuCores(conditions.minCpuCores)) {
                return false;
            }
        }

        // Battery level check
        if (conditions.minBatteryLevel) {
            if (!this.checkMinBatteryLevel(conditions.minBatteryLevel)) {
                return false;
            }
        }

        // Medical context check
        if (conditions.medicalContext && context.medicalPriority) {
            if (!conditions.medicalContext.includes(context.medicalPriority)) {
                return false;
            }
        }

        // Exclude low-end devices
        if (conditions.excludeLowEndDevices && this.isLowEndDevice()) {
            return false;
        }

        // User agent exclusions
        if (conditions.excludeUserAgents) {
            const userAgent = navigator.userAgent.toLowerCase();
            if (conditions.excludeUserAgents.some(exclude => userAgent.includes(exclude.toLowerCase()))) {
                return false;
            }
        }

        return true;
    }

    /**
     * Device and capability detection methods
     */
    isMobileDevice() {
        const userAgent = navigator.userAgent.toLowerCase();
        return /mobile|android|iphone|ipad|ipod/.test(userAgent) || 
               ('ontouchstart' in window && window.screen.width <= 768);
    }

    isHighEndDevice() {
        return (navigator.hardwareConcurrency >= 8) && 
               (navigator.deviceMemory >= 8);
    }

    isLowEndDevice() {
        return (navigator.hardwareConcurrency <= 2) || 
               (navigator.deviceMemory <= 2);
    }

    isBetaTester() {
        // Check URL parameters, localStorage, or other beta tester indicators
        return new URLSearchParams(window.location.search).has('beta') ||
               localStorage.getItem('beta_tester') === 'true';
    }

    checkBrowserVersion(minVersions) {
        // Simplified browser detection
        const userAgent = navigator.userAgent.toLowerCase();
        
        for (const [browser, minVersion] of Object.entries(minVersions)) {
            if (userAgent.includes(browser)) {
                // In a real implementation, you'd parse the actual version
                // For now, assume modern browsers meet requirements
                return true;
            }
        }
        
        return false;
    }

    checkDeviceType(allowedTypes) {
        if (allowedTypes.includes('all')) return true;
        
        if (this.isMobileDevice() && allowedTypes.includes('mobile')) return true;
        if (!this.isMobileDevice() && allowedTypes.includes('desktop')) return true;
        
        return false;
    }

    checkMinMemory(minMemory) {
        return !navigator.deviceMemory || navigator.deviceMemory >= minMemory;
    }

    checkMinCpuCores(minCores) {
        return !navigator.hardwareConcurrency || navigator.hardwareConcurrency >= minCores;
    }

    async checkMinBatteryLevel(minLevel) {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                return battery.charging || battery.level >= minLevel;
            }
        } catch (error) {
            // If battery API is not available, assume OK
            return true;
        }
        return true;
    }

    /**
     * A/B test group assignment
     */
    assignABTestGroups() {
        const userId = this.getUserId();
        const hash = this.hashString(userId);
        
        // Assign to A/B test groups based on hash
        if (hash % 2 === 0) {
            this.userSegments.add('ab_test_group_a');
        } else {
            this.userSegments.add('ab_test_group_b');
        }
    }

    /**
     * Get user ID (could be from session, device fingerprint, etc.)
     */
    getUserId() {
        // Try to get from session storage first
        let userId = sessionStorage.getItem('compression_user_id');
        
        if (!userId) {
            // Generate a device fingerprint-based ID
            const fingerprint = [
                navigator.userAgent,
                navigator.language,
                screen.width + 'x' + screen.height,
                new Date().getTimezoneOffset(),
                navigator.hardwareConcurrency,
                navigator.deviceMemory
            ].join('|');
            
            userId = this.hashString(fingerprint).toString();
            sessionStorage.setItem('compression_user_id', userId);
        }
        
        return userId;
    }

    /**
     * Simple hash function
     */
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash);
    }

    /**
     * Log feature flag evaluation
     */
    logFlagEvaluation(flagName, enabled, reason) {
        if (!this.analyticsEnabled) return;
        
        const logEntry = {
            type: 'flag_evaluation',
            flagName,
            enabled,
            reason,
            timestamp: Date.now(),
            userId: this.getUserId(),
            userSegments: Array.from(this.userSegments)
        };
        
        this.analytics.push(logEntry);
        
        // Keep only last 1000 entries
        if (this.analytics.length > 1000) {
            this.analytics.shift();
        }
    }

    /**
     * Log A/B test variant assignment
     */
    logVariantAssignment(flagName, variant) {
        if (!this.analyticsEnabled) return;
        
        const logEntry = {
            type: 'variant_assignment',
            flagName,
            variant,
            timestamp: Date.now(),
            userId: this.getUserId()
        };
        
        this.analytics.push(logEntry);
    }

    /**
     * Track feature usage
     */
    trackFeatureUsage(featureName, action, metadata = {}) {
        if (!this.analyticsEnabled) return;
        
        const logEntry = {
            type: 'feature_usage',
            featureName,
            action,
            metadata,
            timestamp: Date.now(),
            userId: this.getUserId()
        };
        
        this.analytics.push(logEntry);
    }

    /**
     * Send analytics to server
     */
    sendAnalytics(immediate = false) {
        if (!this.analyticsEnabled || this.analytics.length === 0) return;
        
        const payload = {
            userId: this.getUserId(),
            userSegments: Array.from(this.userSegments),
            events: this.analytics.splice(0), // Remove events after sending
            timestamp: Date.now(),
            deviceInfo: {
                userAgent: navigator.userAgent,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                platform: navigator.platform
            }
        };
        
        // In a real implementation, send to analytics endpoint
        if (immediate) {
            // Use sendBeacon for immediate sending on page unload
            if ('sendBeacon' in navigator) {
                navigator.sendBeacon('/api/compression-analytics/', JSON.stringify(payload));
            }
        } else {
            // Use fetch for regular sending
            fetch('/api/compression-analytics/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(payload)
            }).catch(error => {
                console.warn('Failed to send compression analytics:', error);
            });
        }
        
        console.log('Analytics sent:', payload.events.length, 'events');
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
     * Emergency disable all compression features
     */
    emergencyDisable(reason = 'manual') {
        console.warn('Emergency disable activated:', reason);
        
        // Disable all compression-related flags
        this.flags.forEach((flag, flagName) => {
            if (flagName.includes('compression') || flagName.includes('advanced')) {
                flag.enabled = false;
            }
        });
        
        // Track emergency disable
        this.trackFeatureUsage('emergency_disable', 'activated', { reason });
        
        // Notify UI
        window.dispatchEvent(new CustomEvent('compression-emergency-disable', {
            detail: { reason }
        }));
    }

    /**
     * Get flag status for debugging
     */
    getDebugInfo() {
        return {
            userSegments: Array.from(this.userSegments),
            flags: Object.fromEntries(this.flags),
            userId: this.getUserId(),
            deviceInfo: {
                isMobile: this.isMobileDevice(),
                isHighEnd: this.isHighEndDevice(),
                isLowEnd: this.isLowEndDevice(),
                cpuCores: navigator.hardwareConcurrency,
                memory: navigator.deviceMemory
            },
            recentAnalytics: this.analytics.slice(-10)
        };
    }

    /**
     * Update feature flags from server
     */
    async updateFlags() {
        try {
            const response = await fetch('/api/compression-feature-flags/');
            const serverFlags = await response.json();
            
            // Update flags with server configuration
            for (const [flagName, flagConfig] of Object.entries(serverFlags)) {
                this.flags.set(flagName, {
                    ...this.flags.get(flagName),
                    ...flagConfig,
                    lastUpdated: Date.now()
                });
            }
            
            console.log('Feature flags updated from server');
        } catch (error) {
            console.warn('Failed to update feature flags:', error);
        }
    }
}

// Export for use in other modules
window.CompressionFeatureFlags = CompressionFeatureFlags;