/**
 * ErrorHandling - Comprehensive error handling and recovery for video compression
 * Part of Phase 1: Error Handling Strategy
 */

class CompressionErrorHandler {
    constructor() {
        this.errorHistory = [];
        this.recoveryStrategies = new Map();
        this.interruptions = new Map(); // Track interrupted compressions
        this.medicalContext = null;
        this.setupRecoveryStrategies();
        this.setupMedicalWorkflowHandlers();
    }

    /**
     * Handle compression error with recovery attempts
     */
    async handleError(error, context = {}) {
        const errorInfo = this._analyzeError(error, context);
        this._logError(errorInfo);

        // Check if we should attempt recovery
        if (this._shouldAttemptRecovery(errorInfo)) {
            const recovery = await this._attemptRecovery(errorInfo);
            if (recovery.success) {
                return recovery;
            }
        }

        // Return fallback recommendation
        return this._createFallbackResponse(errorInfo);
    }

    /**
     * Setup recovery strategies for different error types
     */
    setupRecoveryStrategies() {
        // Network interruption recovery
        this.recoveryStrategies.set('network_interruption', {
            retryable: true,
            maxRetries: 3,
            retryDelay: 2000,
            strategy: async (context) => {
                return await this._retryWithDelay(context);
            }
        });

        // Memory exhaustion recovery
        this.recoveryStrategies.set('memory_exhaustion', {
            retryable: true,
            maxRetries: 2,
            retryDelay: 1000,
            strategy: async (context) => {
                return await this._retryWithLowerSettings(context);
            }
        });

        // Device overheating recovery
        this.recoveryStrategies.set('device_overheating', {
            retryable: true,
            maxRetries: 1,
            retryDelay: 10000,
            strategy: async (context) => {
                return await this._retryAfterCooling(context);
            }
        });

        // Browser tab backgrounding recovery
        this.recoveryStrategies.set('tab_backgrounded', {
            retryable: true,
            maxRetries: 2,
            retryDelay: 1000,
            strategy: async (context) => {
                return await this._retryInForeground(context);
            }
        });

        // ffmpeg.wasm loading failure recovery
        this.recoveryStrategies.set('ffmpeg_load_failed', {
            retryable: false,
            maxRetries: 0,
            strategy: async (context) => {
                return { success: false, reason: 'ffmpeg_unavailable' };
            }
        });

        // Compression timeout recovery
        this.recoveryStrategies.set('compression_timeout', {
            retryable: true,
            maxRetries: 1,
            retryDelay: 500,
            strategy: async (context) => {
                return await this._retryWithFasterSettings(context);
            }
        });
    }

    /**
     * Analyze error to determine type and recovery strategy
     */
    _analyzeError(error, context) {
        const errorInfo = {
            type: 'unknown',
            message: error.message || 'Unknown error',
            timestamp: Date.now(),
            context,
            recoverable: false,
            priority: 'medium'
        };

        // Analyze error message and context to determine type
        const message = error.message.toLowerCase();

        if (message.includes('network') || message.includes('fetch')) {
            errorInfo.type = 'network_interruption';
            errorInfo.recoverable = true;
            errorInfo.priority = 'high';
        } else if (message.includes('memory') || message.includes('out of memory')) {
            errorInfo.type = 'memory_exhaustion';
            errorInfo.recoverable = true;
            errorInfo.priority = 'high';
        } else if (message.includes('timeout')) {
            errorInfo.type = 'compression_timeout';
            errorInfo.recoverable = true;
            errorInfo.priority = 'medium';
        } else if (message.includes('background') || message.includes('visibility')) {
            errorInfo.type = 'tab_backgrounded';
            errorInfo.recoverable = true;
            errorInfo.priority = 'low';
        } else if (message.includes('ffmpeg') || message.includes('wasm')) {
            errorInfo.type = 'ffmpeg_load_failed';
            errorInfo.recoverable = false;
            errorInfo.priority = 'critical';
        } else if (message.includes('thermal') || message.includes('overheating')) {
            errorInfo.type = 'device_overheating';
            errorInfo.recoverable = true;
            errorInfo.priority = 'high';
        }

        // Check device conditions
        if (this._isLowBattery()) {
            errorInfo.deviceConditions = { lowBattery: true };
            errorInfo.priority = 'high';
        }

        if (this._isMemoryPressure()) {
            errorInfo.deviceConditions = { memoryPressure: true };
            errorInfo.priority = 'high';
        }

        return errorInfo;
    }

    /**
     * Check if recovery should be attempted
     */
    _shouldAttemptRecovery(errorInfo) {
        // Don't retry if we've had too many recent failures
        const recentErrors = this.errorHistory.filter(
            e => Date.now() - e.timestamp < 300000 // 5 minutes
        );

        if (recentErrors.length >= 5) {
            return false;
        }

        // Don't retry non-recoverable errors
        if (!errorInfo.recoverable) {
            return false;
        }

        // Check if we've already tried this error type recently
        const sameTypeErrors = recentErrors.filter(e => e.type === errorInfo.type);
        const strategy = this.recoveryStrategies.get(errorInfo.type);
        
        return sameTypeErrors.length < (strategy?.maxRetries || 0);
    }

    /**
     * Attempt error recovery
     */
    async _attemptRecovery(errorInfo) {
        const strategy = this.recoveryStrategies.get(errorInfo.type);
        
        if (!strategy) {
            return { success: false, reason: 'no_strategy' };
        }

        try {
            // Wait before retry if specified
            if (strategy.retryDelay) {
                await new Promise(resolve => setTimeout(resolve, strategy.retryDelay));
            }

            return await strategy.strategy(errorInfo.context);
        } catch (recoveryError) {
            return { 
                success: false, 
                reason: 'recovery_failed',
                error: recoveryError.message 
            };
        }
    }

    /**
     * Recovery strategies implementation
     */
    async _retryWithDelay(context) {
        // Simple retry after delay
        return { success: true, action: 'retry', modifications: {} };
    }

    async _retryWithLowerSettings(context) {
        // Retry with more conservative settings
        return {
            success: true,
            action: 'retry',
            modifications: {
                preset: 'mobile-optimized',
                maxOutputSize: context.originalFile?.size * 0.95,
                chunkSize: Math.min(context.chunkSize || Infinity, 25 * 1024 * 1024)
            }
        };
    }

    async _retryAfterCooling(context) {
        // Wait longer for device to cool down
        await new Promise(resolve => setTimeout(resolve, 30000)); // 30 seconds
        return {
            success: true,
            action: 'retry',
            modifications: {
                preset: 'mobile-optimized',
                priority: 'background'
            }
        };
    }

    async _retryInForeground(context) {
        // Check if tab is in foreground, if not, show notification
        if (document.hidden) {
            this._notifyUserFocusRequired();
            return { success: false, reason: 'tab_not_focused' };
        }
        return { success: true, action: 'retry', modifications: {} };
    }

    async _retryWithFasterSettings(context) {
        // Use fastest compression settings
        return {
            success: true,
            action: 'retry',
            modifications: {
                preset: 'mobile-optimized',
                priority: 'speed',
                maxCompressionTime: 30000 // 30 seconds max
            }
        };
    }

    /**
     * Create fallback response when recovery fails
     */
    _createFallbackResponse(errorInfo) {
        const response = {
            success: false,
            fallback: true,
            errorType: errorInfo.type,
            userMessage: this._getUserFriendlyMessage(errorInfo),
            recommendations: this._getRecommendations(errorInfo),
            techDetails: errorInfo.message
        };

        // Add specific actions based on error type
        switch (errorInfo.type) {
            case 'network_interruption':
                response.action = 'retry_later';
                response.userMessage = 'Falha na conexão durante a compressão. Tente novamente quando a conexão estiver estável.';
                break;
            
            case 'memory_exhaustion':
                response.action = 'direct_upload';
                response.userMessage = 'Memória insuficiente para compressão. O arquivo será enviado diretamente.';
                break;
            
            case 'device_overheating':
                response.action = 'wait_and_retry';
                response.userMessage = 'Dispositivo aquecido. Aguarde alguns minutos antes de tentar novamente.';
                break;
            
            case 'ffmpeg_load_failed':
                response.action = 'direct_upload';
                response.userMessage = 'Compressão não disponível neste dispositivo. O arquivo será enviado diretamente.';
                break;
            
            default:
                response.action = 'direct_upload';
                response.userMessage = 'Não foi possível comprimir o vídeo. O arquivo será enviado diretamente.';
        }

        return response;
    }

    /**
     * Get user-friendly error messages
     */
    _getUserFriendlyMessage(errorInfo) {
        const messages = {
            network_interruption: 'Problema de conexão durante a compressão',
            memory_exhaustion: 'Memória insuficiente para processar o arquivo',
            compression_timeout: 'Compressão demorou mais que o esperado',
            tab_backgrounded: 'Compressão pausada - mantenha a aba ativa',
            ffmpeg_load_failed: 'Funcionalidade de compressão não disponível',
            device_overheating: 'Dispositivo aquecido - processamento pausado',
            unknown: 'Erro inesperado durante a compressão'
        };

        return messages[errorInfo.type] || messages.unknown;
    }

    /**
     * Get recommendations for user
     */
    _getRecommendations(errorInfo) {
        const recommendations = {
            network_interruption: [
                'Verifique sua conexão com a internet',
                'Tente novamente quando a conexão estiver estável',
                'Considere usar uma rede mais confiável'
            ],
            memory_exhaustion: [
                'Feche outras abas ou aplicativos',
                'Tente com um arquivo menor',
                'Use o envio direto para arquivos grandes'
            ],
            compression_timeout: [
                'Tente com um arquivo menor',
                'Use configurações de compressão mais rápidas',
                'Considere o envio direto'
            ],
            device_overheating: [
                'Aguarde o dispositivo esfriar',
                'Remova o dispositivo de fontes de calor',
                'Tente novamente em alguns minutos'
            ],
            ffmpeg_load_failed: [
                'Atualize seu navegador',
                'Tente em outro dispositivo',
                'Use o envio direto'
            ]
        };

        return recommendations[errorInfo.type] || ['Tente o envio direto do arquivo'];
    }

    /**
     * Device condition checks
     */
    async _isLowBattery() {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                return !battery.charging && battery.level < 0.2; // Less than 20% and not charging
            }
        } catch (error) {
            console.warn('Battery API unavailable:', error.message);
        }
        return false;
    }

    /**
     * Check for device thermal state
     */
    _isThermalThrottling() {
        // Check for thermal throttling indicators
        try {
            // Performance timing can indicate thermal throttling
            const timing = performance.now();
            const startTime = performance.timing.navigationStart;
            const elapsed = timing - startTime;
            
            // If performance.now() is inconsistent, might indicate throttling
            if (this._lastPerformanceCheck) {
                const expectedElapsed = Date.now() - this._lastPerformanceCheckTime;
                const actualElapsed = timing - this._lastPerformanceCheck;
                const drift = Math.abs(expectedElapsed - actualElapsed);
                
                if (drift > 1000) { // 1 second drift indicates potential throttling
                    return true;
                }
            }
            
            this._lastPerformanceCheck = timing;
            this._lastPerformanceCheckTime = Date.now();
            
            return false;
        } catch (error) {
            return false;
        }
    }

    _isMemoryPressure() {
        if ('memory' in performance) {
            const memInfo = performance.memory;
            const usageRatio = memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit;
            return usageRatio > 0.8; // 80% memory usage
        }
        return false;
    }

    /**
     * Notify user that tab focus is required
     */
    _notifyUserFocusRequired() {
        // In a real implementation, you might show a browser notification
        // or update the UI to indicate focus is needed
        console.log('User focus required for compression to continue');
    }

    /**
     * Log error for debugging and analytics
     */
    _logError(errorInfo) {
        this.errorHistory.push(errorInfo);
        
        // Keep only recent errors (last 24 hours)
        const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
        this.errorHistory = this.errorHistory.filter(e => e.timestamp > oneDayAgo);

        // Log to console for debugging
        console.warn('Compression error:', errorInfo);

        // In a real implementation, you might send to analytics
        this._sendToAnalytics(errorInfo);
    }

    /**
     * Send error data to analytics (placeholder)
     */
    _sendToAnalytics(errorInfo) {
        // Placeholder for analytics integration
        // In production, you'd send to your analytics service
        console.log('Analytics: Compression error', {
            type: errorInfo.type,
            priority: errorInfo.priority,
            recoverable: errorInfo.recoverable,
            userAgent: navigator.userAgent.substring(0, 100)
        });
    }

    /**
     * Get error statistics for monitoring
     */
    getErrorStats() {
        const stats = {
            totalErrors: this.errorHistory.length,
            errorsByType: {},
            recentErrors: 0,
            criticalErrors: 0
        };

        const recentThreshold = Date.now() - (60 * 60 * 1000); // 1 hour ago

        this.errorHistory.forEach(error => {
            // Count by type
            stats.errorsByType[error.type] = (stats.errorsByType[error.type] || 0) + 1;
            
            // Count recent errors
            if (error.timestamp > recentThreshold) {
                stats.recentErrors++;
            }
            
            // Count critical errors
            if (error.priority === 'critical') {
                stats.criticalErrors++;
            }
        });

        return stats;
    }

    /**
     * Setup medical workflow specific handlers
     */
    setupMedicalWorkflowHandlers() {
        // Emergency bypass - always available
        this.emergencyBypass = {
            enabled: true,
            reason: null,
            timestamp: null
        };

        // Medical context priorities
        this.medicalPriorities = {
            emergency: { timeout: 15000, skipCompression: true },
            urgent: { timeout: 30000, fallbackQuick: true },
            routine: { timeout: 60000, allowRetries: true }
        };

        // Page visibility change handler for medical workflows
        document.addEventListener('visibilitychange', () => {
            this._handleVisibilityChange();
        });

        // Beforeunload handler to save compression state
        window.addEventListener('beforeunload', (e) => {
            this._saveCompressionState();
        });
    }

    /**
     * Set medical context for prioritized error handling
     */
    setMedicalContext(context) {
        this.medicalContext = {
            priority: context.priority || 'routine', // emergency, urgent, routine
            patientId: context.patientId,
            emergencyCase: context.emergencyCase || false,
            workflowStep: context.workflowStep || 'documentation'
        };
    }

    /**
     * Check if compression should be skipped for medical emergency
     */
    shouldSkipCompression() {
        if (!this.medicalContext) return false;

        // Skip compression for emergency cases
        if (this.medicalContext.priority === 'emergency' || this.medicalContext.emergencyCase) {
            return true;
        }

        // Skip if emergency bypass is active
        if (this.emergencyBypass.enabled && this.emergencyBypass.reason) {
            return true;
        }

        return false;
    }

    /**
     * Activate emergency bypass
     */
    activateEmergencyBypass(reason = 'user_requested') {
        this.emergencyBypass = {
            enabled: true,
            reason: reason,
            timestamp: Date.now()
        };

        console.log('Emergency bypass activated:', reason);
        
        // Notify user
        this._showMedicalEmergencyMessage();
    }

    /**
     * Handle page visibility changes for medical workflows
     */
    _handleVisibilityChange() {
        if (document.hidden) {
            // Page became hidden - save current compression state
            this._saveCompressionState();
        } else {
            // Page became visible - check for resumed compressions
            this._checkResumedCompressions();
        }
    }

    /**
     * Save compression state for potential resume
     */
    _saveCompressionState() {
        const activeCompressions = this._getActiveCompressions();
        
        if (activeCompressions.length > 0) {
            const stateData = {
                compressions: activeCompressions,
                timestamp: Date.now(),
                medicalContext: this.medicalContext
            };

            try {
                sessionStorage.setItem('videoCompressionState', JSON.stringify(stateData));
            } catch (error) {
                console.warn('Failed to save compression state:', error);
            }
        }
    }

    /**
     * Check for compressions that can be resumed
     */
    _checkResumedCompressions() {
        try {
            const savedState = sessionStorage.getItem('videoCompressionState');
            if (!savedState) return;

            const stateData = JSON.parse(savedState);
            const timeSinceInterruption = Date.now() - stateData.timestamp;

            // Only attempt resume if interruption was recent (< 5 minutes)
            if (timeSinceInterruption < 300000) {
                this._offerCompressionResume(stateData);
            } else {
                // Clean up old state
                sessionStorage.removeItem('videoCompressionState');
            }
        } catch (error) {
            console.warn('Failed to check resumed compressions:', error);
        }
    }

    /**
     * Offer to resume interrupted compression
     */
    _offerCompressionResume(stateData) {
        const message = 'Compressão de vídeo foi interrompida. Deseja continuar onde parou?';
        
        if (confirm(message)) {
            // Attempt to resume compression
            this._resumeCompressions(stateData.compressions);
        } else {
            // User declined, offer direct upload
            this._offerDirectUpload(stateData.compressions);
        }
        
        // Clean up saved state
        sessionStorage.removeItem('videoCompressionState');
    }

    /**
     * Resume interrupted compressions
     */
    async _resumeCompressions(compressions) {
        for (const compression of compressions) {
            try {
                // Attempt to restart compression from where it left off
                await this._restartCompression(compression);
            } catch (error) {
                console.warn('Failed to resume compression:', error);
                // Fall back to direct upload for this file
                this._fallbackToDirectUpload(compression);
            }
        }
    }

    /**
     * Get currently active compressions
     */
    _getActiveCompressions() {
        // This would integrate with the compression manager
        // For now, return empty array - actual implementation would track active compressions
        return [];
    }

    /**
     * Restart a specific compression
     */
    async _restartCompression(compressionData) {
        // Implementation would depend on the compression manager
        // This is a placeholder for the restart logic
        console.log('Restarting compression:', compressionData.fileName);
    }

    /**
     * Offer direct upload as fallback
     */
    _offerDirectUpload(compressions) {
        const fileCount = compressions.length;
        const message = fileCount === 1 
            ? 'Enviar arquivo diretamente sem compressão?'
            : `Enviar ${fileCount} arquivos diretamente sem compressão?`;
            
        if (confirm(message)) {
            compressions.forEach(compression => {
                this._fallbackToDirectUpload(compression);
            });
        }
    }

    /**
     * Fallback to direct upload
     */
    _fallbackToDirectUpload(compressionData) {
        // This would trigger the direct upload mechanism
        console.log('Falling back to direct upload:', compressionData.fileName);
        
        // Dispatch custom event that the upload form can listen to
        const event = new CustomEvent('compressionFallback', {
            detail: {
                file: compressionData.file,
                reason: 'user_choice'
            }
        });
        
        document.dispatchEvent(event);
    }

    /**
     * Show medical emergency message
     */
    _showMedicalEmergencyMessage() {
        const message = 'Modo de emergência ativado. Arquivos serão enviados diretamente sem compressão para agilizar o processo.';
        
        // In a real implementation, this would show a proper medical UI notification
        if (typeof window.showMedicalNotification === 'function') {
            window.showMedicalNotification(message, 'warning');
        } else {
            console.warn('Medical Emergency Mode:', message);
        }
    }

    /**
     * Enhanced error analysis with medical context
     */
    _analyzeError(error, context) {
        const errorInfo = {
            type: 'unknown',
            message: error.message || 'Unknown error',
            timestamp: Date.now(),
            context,
            recoverable: false,
            priority: 'medium',
            medicalImpact: 'low'
        };

        // Enhanced error analysis with medical context
        const message = error.message.toLowerCase();

        if (message.includes('network') || message.includes('fetch')) {
            errorInfo.type = 'network_interruption';
            errorInfo.recoverable = true;
            errorInfo.priority = this.medicalContext?.priority === 'emergency' ? 'critical' : 'high';
            errorInfo.medicalImpact = this.medicalContext?.priority === 'emergency' ? 'high' : 'medium';
        } else if (message.includes('memory') || message.includes('out of memory')) {
            errorInfo.type = 'memory_exhaustion';
            errorInfo.recoverable = true;
            errorInfo.priority = 'high';
            errorInfo.medicalImpact = 'medium';
        } else if (message.includes('timeout')) {
            errorInfo.type = 'compression_timeout';
            errorInfo.recoverable = true;
            errorInfo.priority = this.medicalContext?.priority === 'emergency' ? 'high' : 'medium';
            errorInfo.medicalImpact = this.medicalContext?.priority === 'emergency' ? 'high' : 'low';
        } else if (message.includes('background') || message.includes('visibility')) {
            errorInfo.type = 'tab_backgrounded';
            errorInfo.recoverable = true;
            errorInfo.priority = 'low';
            errorInfo.medicalImpact = 'low';
        } else if (message.includes('ffmpeg') || message.includes('wasm')) {
            errorInfo.type = 'ffmpeg_load_failed';
            errorInfo.recoverable = false;
            errorInfo.priority = 'critical';
            errorInfo.medicalImpact = 'low'; // Direct upload still works
        } else if (message.includes('thermal') || message.includes('overheating')) {
            errorInfo.type = 'device_overheating';
            errorInfo.recoverable = true;
            errorInfo.priority = 'high';
            errorInfo.medicalImpact = 'medium';
        }

        // Check device conditions with async battery check
        this._isLowBattery().then(isLowBattery => {
            if (isLowBattery) {
                errorInfo.deviceConditions = { lowBattery: true };
                errorInfo.priority = 'high';
                errorInfo.medicalImpact = 'high';
            }
        });

        if (this._isMemoryPressure()) {
            errorInfo.deviceConditions = { memoryPressure: true };
            errorInfo.priority = 'high';
        }

        if (this._isThermalThrottling()) {
            errorInfo.deviceConditions = { thermalThrottling: true };
            errorInfo.priority = 'high';
        }

        return errorInfo;
    }

    /**
     * Enhanced fallback response with medical workflow considerations
     */
    _createFallbackResponse(errorInfo) {
        const response = {
            success: false,
            fallback: true,
            errorType: errorInfo.type,
            userMessage: this._getUserFriendlyMessage(errorInfo),
            recommendations: this._getRecommendations(errorInfo),
            techDetails: errorInfo.message,
            medicalWorkflow: {
                allowDirectUpload: true,
                emergencyBypass: this.shouldSkipCompression(),
                urgencyLevel: this.medicalContext?.priority || 'routine'
            }
        };

        // Medical workflow specific actions
        if (this.medicalContext?.priority === 'emergency' || this.medicalContext?.emergencyCase) {
            response.action = 'direct_upload_immediate';
            response.userMessage = 'Caso de emergência detectado. Arquivo será enviado imediatamente sem compressão.';
            response.medicalWorkflow.skipAllProcessing = true;
        } else {
            // Add specific actions based on error type
            switch (errorInfo.type) {
                case 'network_interruption':
                    response.action = this.medicalContext?.priority === 'urgent' ? 'direct_upload' : 'retry_later';
                    response.userMessage = this.medicalContext?.priority === 'urgent' 
                        ? 'Caso urgente: Arquivo será enviado diretamente devido a problema de conexão.'
                        : 'Falha na conexão durante a compressão. Tente novamente quando a conexão estiver estável.';
                    break;
                
                case 'memory_exhaustion':
                    response.action = 'direct_upload';
                    response.userMessage = 'Memória insuficiente para compressão. O arquivo será enviado diretamente.';
                    break;
                
                case 'device_overheating':
                    response.action = this.medicalContext?.priority === 'urgent' ? 'direct_upload' : 'wait_and_retry';
                    response.userMessage = this.medicalContext?.priority === 'urgent'
                        ? 'Dispositivo aquecido. Enviando diretamente devido à urgência do caso.'
                        : 'Dispositivo aquecido. Aguarde alguns minutos antes de tentar novamente.';
                    break;
                
                case 'ffmpeg_load_failed':
                    response.action = 'direct_upload';
                    response.userMessage = 'Compressão não disponível neste dispositivo. O arquivo será enviado diretamente.';
                    break;
                
                default:
                    response.action = 'direct_upload';
                    response.userMessage = 'Não foi possível comprimir o vídeo. O arquivo será enviado diretamente.';
            }
        }

        return response;
    }

    /**
     * Clear error history
     */
    clearErrorHistory() {
        this.errorHistory = [];
    }

    /**
     * Clean up resources and saved states
     */
    cleanup() {
        this.clearErrorHistory();
        try {
            sessionStorage.removeItem('videoCompressionState');
        } catch (error) {
            console.warn('Failed to clean up compression state:', error);
        }
    }
}

// Export for use in other modules
window.CompressionErrorHandler = CompressionErrorHandler;