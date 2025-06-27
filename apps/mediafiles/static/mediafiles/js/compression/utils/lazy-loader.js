/**
 * LazyLoader - Lazy loading system for compression modules
 * Part of Phase 3: Performance Optimization - Lazy Loading Strategy
 */

class CompressionLazyLoader {
    constructor() {
        this.loadedModules = new Set();
        this.loadingPromises = new Map();
        this.moduleConfigs = new Map();
        this.cacheEnabled = true;
        this.cacheExpiryTime = 24 * 60 * 60 * 1000; // 24 hours
        
        this.setupModuleConfigurations();
        this.setupCaching();
    }

    /**
     * Setup module configurations
     */
    setupModuleConfigurations() {
        // Core compression modules
        this.moduleConfigs.set('ffmpeg-core', {
            url: 'https://unpkg.com/@ffmpeg/core@0.12.4/dist/esm/ffmpeg-core.js',
            type: 'module',
            size: 1300000, // ~1.3MB
            critical: true,
            dependencies: []
        });

        this.moduleConfigs.set('ffmpeg-wasm', {
            url: 'https://unpkg.com/@ffmpeg/ffmpeg@0.12.4/dist/esm/index.js',
            type: 'module',
            size: 50000, // ~50KB
            critical: true,
            dependencies: ['ffmpeg-core']
        });

        // Image processing modules (for thumbnails)
        this.moduleConfigs.set('image-processing', {
            url: '/static/mediafiles/js/compression/modules/image-processing.js',
            type: 'script',
            size: 75000, // ~75KB
            critical: false,
            dependencies: []
        });

        // Advanced compression utilities
        this.moduleConfigs.set('advanced-codecs', {
            url: '/static/mediafiles/js/compression/modules/advanced-codecs.js',
            type: 'script',
            size: 120000, // ~120KB
            critical: false,
            dependencies: ['ffmpeg-wasm']
        });

        // Medical workflow enhancements
        this.moduleConfigs.set('medical-workflows', {
            url: '/static/mediafiles/js/compression/ui/medical-workflows.js',
            type: 'script',
            size: 25000, // ~25KB
            critical: false,
            dependencies: []
        });

        // Performance monitoring
        this.moduleConfigs.set('performance-monitor', {
            url: '/static/mediafiles/js/compression/utils/performance-monitor.js',
            type: 'script',
            size: 35000, // ~35KB
            critical: false,
            dependencies: []
        });
    }

    /**
     * Setup caching system
     */
    setupCaching() {
        if ('caches' in window) {
            this.setupServiceWorkerCache();
        } else {
            // Fallback to memory cache
            this.moduleCache = new Map();
        }
    }

    /**
     * Setup service worker cache for modules
     */
    async setupServiceWorkerCache() {
        try {
            this.cache = await caches.open('compression-modules-v1');
            console.log('Service worker cache available for compression modules');
        } catch (error) {
            console.warn('Service worker cache not available:', error);
            this.moduleCache = new Map();
        }
    }

    /**
     * Load module with lazy loading
     */
    async loadModule(moduleName, options = {}) {
        // Check if already loaded
        if (this.loadedModules.has(moduleName)) {
            return true;
        }

        // Check if already loading
        if (this.loadingPromises.has(moduleName)) {
            return await this.loadingPromises.get(moduleName);
        }

        const moduleConfig = this.moduleConfigs.get(moduleName);
        if (!moduleConfig) {
            throw new Error(`Unknown module: ${moduleName}`);
        }

        // Create loading promise
        const loadingPromise = this._loadModuleInternal(moduleName, moduleConfig, options);
        this.loadingPromises.set(moduleName, loadingPromise);

        try {
            const result = await loadingPromise;
            this.loadedModules.add(moduleName);
            return result;
        } finally {
            this.loadingPromises.delete(moduleName);
        }
    }

    /**
     * Internal module loading logic
     */
    async _loadModuleInternal(moduleName, moduleConfig, options) {
        console.log(`Loading module: ${moduleName}`);
        
        // Load dependencies first
        if (moduleConfig.dependencies.length > 0) {
            await this.loadDependencies(moduleConfig.dependencies);
        }

        // Check device capabilities for heavy modules
        if (moduleConfig.size > 100000 && !this.checkDeviceCapabilities(moduleConfig)) {
            throw new Error(`Device not capable of loading module: ${moduleName}`);
        }

        // Check network conditions for large modules
        if (moduleConfig.size > 500000 && !await this.checkNetworkConditions()) {
            if (!options.forceLoad) {
                throw new Error(`Network conditions not suitable for loading ${moduleName}`);
            }
        }

        // Try to load from cache first
        const cachedModule = await this.loadFromCache(moduleName, moduleConfig);
        if (cachedModule) {
            return await this.executeModule(moduleName, moduleConfig, cachedModule);
        }

        // Load from network
        return await this.loadFromNetwork(moduleName, moduleConfig);
    }

    /**
     * Load module dependencies
     */
    async loadDependencies(dependencies) {
        const loadPromises = dependencies.map(dep => this.loadModule(dep));
        await Promise.all(loadPromises);
    }

    /**
     * Check device capabilities
     */
    checkDeviceCapabilities(moduleConfig) {
        // Check memory
        if (navigator.deviceMemory && navigator.deviceMemory < 2) {
            console.warn('Low device memory, skipping heavy module:', moduleConfig);
            return false;
        }

        // Check CPU cores
        if (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 2) {
            console.warn('Low CPU cores, skipping heavy module:', moduleConfig);
            return false;
        }

        // Check if mobile device with large module
        if (this.isMobileDevice() && moduleConfig.size > 1000000) {
            console.warn('Mobile device with large module, checking further...');
            
            // Allow only if user explicitly requested or device is high-end
            return this.isHighEndMobileDevice();
        }

        return true;
    }

    /**
     * Check network conditions
     */
    async checkNetworkConditions() {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        
        if (!connection) {
            // Assume reasonable network if API not available
            return true;
        }

        // Block on very slow connections
        if (connection.effectiveType === 'slow-2g') {
            return false;
        }

        // Allow on good connections
        if (connection.effectiveType === '4g' || connection.downlink > 5) {
            return true;
        }

        // For moderate connections, check if user is on metered connection
        if (connection.saveData) {
            return false;
        }

        return true;
    }

    /**
     * Load module from cache
     */
    async loadFromCache(moduleName, moduleConfig) {
        try {
            if (this.cache) {
                // Try service worker cache
                const response = await this.cache.match(moduleConfig.url);
                if (response) {
                    const cacheTime = response.headers.get('cache-time');
                    if (cacheTime && Date.now() - parseInt(cacheTime) < this.cacheExpiryTime) {
                        console.log(`Loaded ${moduleName} from service worker cache`);
                        return await response.text();
                    }
                }
            } else if (this.moduleCache) {
                // Try memory cache
                const cached = this.moduleCache.get(moduleName);
                if (cached && Date.now() - cached.timestamp < this.cacheExpiryTime) {
                    console.log(`Loaded ${moduleName} from memory cache`);
                    return cached.content;
                }
            }
        } catch (error) {
            console.warn(`Cache miss for ${moduleName}:`, error);
        }

        return null;
    }

    /**
     * Load module from network
     */
    async loadFromNetwork(moduleName, moduleConfig) {
        console.log(`Loading ${moduleName} from network...`);
        
        try {
            // Add loading indicator for large modules
            if (moduleConfig.size > 500000) {
                this.showLoadingIndicator(moduleName, moduleConfig.size);
            }

            const response = await fetch(moduleConfig.url);
            
            if (!response.ok) {
                throw new Error(`Failed to load ${moduleName}: ${response.status}`);
            }

            const content = await response.text();
            
            // Cache the module
            await this.cacheModule(moduleName, moduleConfig, content);
            
            // Execute the module
            return await this.executeModule(moduleName, moduleConfig, content);

        } catch (error) {
            console.error(`Failed to load module ${moduleName}:`, error);
            throw error;
        } finally {
            this.hideLoadingIndicator(moduleName);
        }
    }

    /**
     * Cache loaded module
     */
    async cacheModule(moduleName, moduleConfig, content) {
        if (!this.cacheEnabled) return;

        try {
            if (this.cache) {
                // Cache in service worker
                const response = new Response(content, {
                    headers: {
                        'Content-Type': 'application/javascript',
                        'cache-time': Date.now().toString()
                    }
                });
                await this.cache.put(moduleConfig.url, response);
            } else if (this.moduleCache) {
                // Cache in memory
                this.moduleCache.set(moduleName, {
                    content,
                    timestamp: Date.now()
                });
            }
            
            console.log(`Cached module: ${moduleName}`);
        } catch (error) {
            console.warn(`Failed to cache ${moduleName}:`, error);
        }
    }

    /**
     * Execute loaded module
     */
    async executeModule(moduleName, moduleConfig, content) {
        try {
            if (moduleConfig.type === 'module') {
                // Handle ES modules
                const blob = new Blob([content], { type: 'application/javascript' });
                const moduleUrl = URL.createObjectURL(blob);
                const module = await import(moduleUrl);
                URL.revokeObjectURL(moduleUrl);
                return module;
            } else {
                // Handle regular scripts
                const script = document.createElement('script');
                script.textContent = content;
                document.head.appendChild(script);
                
                // Wait for script to execute
                await new Promise(resolve => {
                    script.onload = resolve;
                    if (script.readyState === 'complete') resolve();
                });
                
                return true;
            }
        } catch (error) {
            console.error(`Failed to execute module ${moduleName}:`, error);
            throw error;
        }
    }

    /**
     * Preload critical modules
     */
    async preloadCriticalModules() {
        const criticalModules = Array.from(this.moduleConfigs.entries())
            .filter(([name, config]) => config.critical)
            .map(([name]) => name);

        console.log('Preloading critical modules:', criticalModules);

        const preloadPromises = criticalModules.map(module => 
            this.loadModule(module, { forceLoad: true })
                .catch(error => {
                    console.warn(`Failed to preload critical module ${module}:`, error);
                    return false;
                })
        );

        const results = await Promise.all(preloadPromises);
        const successCount = results.filter(Boolean).length;
        
        console.log(`Preloaded ${successCount}/${criticalModules.length} critical modules`);
        return successCount === criticalModules.length;
    }

    /**
     * Load modules for specific use case
     */
    async loadForUseCase(useCase, options = {}) {
        const moduleMap = {
            'basic_compression': ['ffmpeg-wasm', 'performance-monitor'],
            'advanced_compression': ['ffmpeg-wasm', 'advanced-codecs', 'performance-monitor'],
            'medical_workflow': ['ffmpeg-wasm', 'medical-workflows', 'performance-monitor'],
            'thumbnail_generation': ['image-processing'],
            'full_suite': ['ffmpeg-wasm', 'advanced-codecs', 'image-processing', 'medical-workflows', 'performance-monitor']
        };

        const modules = moduleMap[useCase];
        if (!modules) {
            throw new Error(`Unknown use case: ${useCase}`);
        }

        console.log(`Loading modules for use case: ${useCase}`);
        
        const loadPromises = modules.map(module => 
            this.loadModule(module, options)
                .catch(error => {
                    console.warn(`Failed to load module ${module} for ${useCase}:`, error);
                    return false;
                })
        );

        const results = await Promise.all(loadPromises);
        const successCount = results.filter(Boolean).length;
        
        console.log(`Loaded ${successCount}/${modules.length} modules for ${useCase}`);
        return results;
    }

    /**
     * Show loading indicator for large modules
     */
    showLoadingIndicator(moduleName, size) {
        const indicator = document.createElement('div');
        indicator.id = `loading-${moduleName}`;
        indicator.className = 'compression-loading-indicator';
        indicator.innerHTML = `
            <div class="spinner"></div>
            <div class="message">Carregando módulo de compressão... (${Math.round(size / 1024)}KB)</div>
        `;
        
        // Add to page if not already present
        if (!document.getElementById(indicator.id)) {
            document.body.appendChild(indicator);
        }
    }

    /**
     * Hide loading indicator
     */
    hideLoadingIndicator(moduleName) {
        const indicator = document.getElementById(`loading-${moduleName}`);
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Check if device is mobile
     */
    isMobileDevice() {
        const userAgent = navigator.userAgent.toLowerCase();
        return /mobile|android|iphone|ipad|ipod/.test(userAgent) || 
               ('ontouchstart' in window && window.screen.width <= 768);
    }

    /**
     * Check if device is high-end mobile
     */
    isHighEndMobileDevice() {
        // High-end mobile devices typically have more cores and memory
        return (navigator.hardwareConcurrency >= 6) && 
               (navigator.deviceMemory >= 4);
    }

    /**
     * Get loading status
     */
    getLoadingStatus() {
        return {
            loadedModules: Array.from(this.loadedModules),
            loadingModules: Array.from(this.loadingPromises.keys()),
            availableModules: Array.from(this.moduleConfigs.keys()),
            cacheEnabled: this.cacheEnabled
        };
    }

    /**
     * Clear module cache
     */
    async clearCache() {
        try {
            if (this.cache) {
                await this.cache.clear();
            }
            
            if (this.moduleCache) {
                this.moduleCache.clear();
            }
            
            console.log('Module cache cleared');
        } catch (error) {
            console.warn('Failed to clear cache:', error);
        }
    }

    /**
     * Get cache statistics
     */
    async getCacheStats() {
        const stats = {
            enabled: this.cacheEnabled,
            type: this.cache ? 'service-worker' : 'memory',
            entries: 0,
            size: 0
        };

        try {
            if (this.cache) {
                const keys = await this.cache.keys();
                stats.entries = keys.length;
                
                for (const request of keys) {
                    const response = await this.cache.match(request);
                    if (response) {
                        const blob = await response.blob();
                        stats.size += blob.size;
                    }
                }
            } else if (this.moduleCache) {
                stats.entries = this.moduleCache.size;
                stats.size = Array.from(this.moduleCache.values())
                    .reduce((total, cached) => total + cached.content.length, 0);
            }
        } catch (error) {
            console.warn('Failed to get cache stats:', error);
        }

        return stats;
    }

    /**
     * Clean up lazy loader
     */
    cleanup() {
        // Clear loading promises
        this.loadingPromises.clear();
        
        // Remove loading indicators
        document.querySelectorAll('.compression-loading-indicator').forEach(el => el.remove());
        
        console.log('Lazy loader cleaned up');
    }
}

// Export for use in other modules
window.CompressionLazyLoader = CompressionLazyLoader;