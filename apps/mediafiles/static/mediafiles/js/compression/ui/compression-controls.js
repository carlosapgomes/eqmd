/**
 * CompressionControls - UI components for video compression
 * Provides toggles, presets, progress, and emergency controls
 */
class CompressionControls {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            showPresets: true,
            showProgress: true,
            showEmergencyBypass: true,
            medicalContext: null,
            ...options
        };
        this.state = {
            compressionEnabled: false,
            selectedPreset: 'medical-standard',
            isCompressing: false,
            progress: 0
        };
        this.init();
    }

    /**
     * Initialize compression controls
     */
    init() {
        this.createCompressionToggle();
        this.createPresetSelector();
        this.createProgressIndicator();
        this.createEmergencyBypass();
        this.setupEventHandlers();
    }

    /**
     * Create compression enable/disable toggle
     */
    createCompressionToggle() {
        const toggleHtml = `
            <div class="compression-toggle-container mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch" 
                           id="compressionToggle" ${this.state.compressionEnabled ? 'checked' : ''}>
                    <label class="form-check-label fw-bold" for="compressionToggle">
                        <i class="bi bi-cpu me-1"></i>
                        Comprimir vídeo antes do envio
                    </label>
                </div>
                <div class="form-text">
                    <i class="bi bi-info-circle me-1"></i>
                    Reduz o tamanho do arquivo mantendo a qualidade médica necessária
                </div>
            </div>
        `;
        this.container.insertAdjacentHTML('afterbegin', toggleHtml);
    }

    /**
     * Create quality preset selector
     */
    createPresetSelector() {
        const presetHtml = `
            <div class="compression-presets" id="compressionPresets" style="display: none;">
                <label class="form-label fw-bold mb-2">
                    <i class="bi bi-sliders me-1"></i>
                    Qualidade de Compressão
                </label>
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="compression-preset-card" data-preset="medical-high">
                            <div class="preset-header">
                                <i class="bi bi-award text-primary"></i>
                                <span class="preset-name">Alta Qualidade</span>
                            </div>
                            <div class="preset-description">
                                Ideal para conteúdo diagnóstico
                            </div>
                            <div class="preset-specs">
                                <small class="text-muted">
                                    • Qualidade: 95%<br>
                                    • Redução: ~30%<br>
                                    • Tempo: +30s
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="compression-preset-card active" data-preset="medical-standard">
                            <div class="preset-header">
                                <i class="bi bi-check-circle text-success"></i>
                                <span class="preset-name">Padrão Médico</span>
                            </div>
                            <div class="preset-description">
                                Equilibrio entre qualidade e tamanho
                            </div>
                            <div class="preset-specs">
                                <small class="text-muted">
                                    • Qualidade: 85%<br>
                                    • Redução: ~50%<br>
                                    • Tempo: +15s
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="compression-preset-card" data-preset="mobile-optimized">
                            <div class="preset-header">
                                <i class="bi bi-phone text-info"></i>
                                <span class="preset-name">Otimizado</span>
                            </div>
                            <div class="preset-description">
                                Rápido para dispositivos móveis
                            </div>
                            <div class="preset-specs">
                                <small class="text-muted">
                                    • Qualidade: 75%<br>
                                    • Redução: ~70%<br>
                                    • Tempo: +10s
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        this.container.insertAdjacentHTML('beforeend', presetHtml);
    }

    /**
     * Create progress indicator
     */
    createProgressIndicator() {
        const progressHtml = `
            <div class="compression-progress-container" id="compressionProgress" style="display: none;">
                <div class="progress-header mb-2">
                    <span class="progress-label">Comprimindo vídeo...</span>
                    <span class="progress-percentage">0%</span>
                </div>
                <div class="progress mb-2" style="height: 8px;">
                    <div class="progress-bar bg-medical-primary" role="progressbar" 
                         style="width: 0%" id="compressionProgressBar"></div>
                </div>
                <div class="progress-details">
                    <small class="text-muted">
                        <span id="compressionStage">Inicializando...</span>
                        <span class="float-end">
                            <span id="compressionETA">Calculando tempo...</span>
                        </span>
                    </small>
                </div>
                <div class="progress-actions mt-2">
                    <button type="button" class="btn btn-sm btn-outline-secondary" id="cancelCompression">
                        <i class="bi bi-x-circle me-1"></i>
                        Cancelar e Enviar Direto
                    </button>
                </div>
            </div>
        `;
        this.container.insertAdjacentHTML('beforeend', progressHtml);
    }

    /**
     * Create emergency bypass button
     */
    createEmergencyBypass() {
        const emergencyHtml = `
            <div class="emergency-bypass-container mt-3">
                <button type="button" class="btn btn-outline-danger btn-sm" id="emergencyBypass">
                    <i class="bi bi-exclamation-triangle me-1"></i>
                    Emergência: Enviar Imediatamente
                </button>
                <div class="form-text">
                    <small class="text-muted">
                        Para casos de emergência médica que requerem envio imediato
                    </small>
                </div>
            </div>
        `;
        this.container.insertAdjacentHTML('beforeend', emergencyHtml);
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Compression toggle
        const toggle = document.getElementById('compressionToggle');
        toggle?.addEventListener('change', (e) => {
            this.toggleCompression(e.target.checked);
        });

        // Preset selection
        document.querySelectorAll('.compression-preset-card').forEach(card => {
            card.addEventListener('click', () => {
                this.selectPreset(card.dataset.preset);
            });
        });

        // Cancel compression
        document.getElementById('cancelCompression')?.addEventListener('click', () => {
            this.cancelCompression();
        });

        // Emergency bypass
        document.getElementById('emergencyBypass')?.addEventListener('click', () => {
            this.activateEmergencyBypass();
        });
    }

    /**
     * Toggle compression on/off
     */
    toggleCompression(enabled) {
        this.state.compressionEnabled = enabled;
        const presets = document.getElementById('compressionPresets');
        
        if (enabled) {
            presets.style.display = 'block';
            this.emit('compressionEnabled', { preset: this.state.selectedPreset });
        } else {
            presets.style.display = 'none';
            this.emit('compressionDisabled');
        }
    }

    /**
     * Select compression preset
     */
    selectPreset(preset) {
        // Remove active class from all cards
        document.querySelectorAll('.compression-preset-card').forEach(card => {
            card.classList.remove('active');
        });

        // Add active class to selected card
        document.querySelector(`[data-preset="${preset}"]`).classList.add('active');
        
        this.state.selectedPreset = preset;
        this.emit('presetSelected', { preset });
    }

    /**
     * Update compression progress
     */
    updateProgress(stage, progress, eta = null) {
        const progressContainer = document.getElementById('compressionProgress');
        const progressBar = document.getElementById('compressionProgressBar');
        const progressPercentage = progressContainer.querySelector('.progress-percentage');
        const stageElement = document.getElementById('compressionStage');
        const etaElement = document.getElementById('compressionETA');

        if (!this.state.isCompressing) {
            progressContainer.style.display = 'block';
            this.state.isCompressing = true;
        }

        // Update progress bar
        progressBar.style.width = `${progress}%`;
        progressPercentage.textContent = `${Math.round(progress)}%`;

        // Update stage
        const stageMessages = {
            initializing: 'Inicializando compressão...',
            loading: 'Carregando módulos...',
            processing: 'Comprimindo vídeo...',
            finalizing: 'Finalizando...',
            completed: 'Compressão concluída!'
        };
        stageElement.textContent = stageMessages[stage] || stage;

        // Update ETA
        if (eta) {
            etaElement.textContent = `${eta}s restantes`;
        }

        // Emit progress event
        this.emit('progressUpdate', { stage, progress, eta });
    }

    /**
     * Complete compression
     */
    completeCompression(result) {
        const progressContainer = document.getElementById('compressionProgress');
        progressContainer.style.display = 'none';
        this.state.isCompressing = false;
        
        // Show completion message
        const completionMsg = `
            <div class="alert alert-success" role="alert">
                <i class="bi bi-check-circle me-2"></i>
                <strong>Compressão concluída!</strong>
                Arquivo reduzido em ${Math.round((1 - result.compressionRatio) * 100)}%
            </div>
        `;
        this.container.insertAdjacentHTML('beforeend', completionMsg);
        
        this.emit('compressionComplete', result);
    }

    /**
     * Handle compression error
     */
    handleCompressionError(error) {
        const progressContainer = document.getElementById('compressionProgress');
        progressContainer.style.display = 'none';
        this.state.isCompressing = false;
        
        // Show error message with fallback option
        const errorMsg = `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Falha na compressão:</strong> ${error.message}
                <div class="mt-2">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="this.parentElement.parentElement.remove()">
                        <i class="bi bi-upload me-1"></i>
                        Continuar com envio direto
                    </button>
                </div>
            </div>
        `;
        this.container.insertAdjacentHTML('beforeend', errorMsg);
        
        this.emit('compressionError', error);
    }

    /**
     * Cancel compression
     */
    cancelCompression() {
        this.state.isCompressing = false;
        document.getElementById('compressionProgress').style.display = 'none';
        this.emit('compressionCancelled');
    }

    /**
     * Activate emergency bypass
     */
    activateEmergencyBypass() {
        if (confirm('Ativar modo de emergência? O vídeo será enviado imediatamente sem compressão.')) {
            this.state.compressionEnabled = false;
            document.getElementById('compressionToggle').checked = false;
            document.getElementById('compressionPresets').style.display = 'none';
            
            // Show emergency status
            const emergencyMsg = `
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>Modo de Emergência Ativado</strong>
                    O arquivo será enviado imediatamente sem compressão.
                </div>
            `;
            this.container.insertAdjacentHTML('afterbegin', emergencyMsg);
            
            this.emit('emergencyBypass');
        }
    }

    /**
     * Get current compression settings
     */
    getSettings() {
        return {
            enabled: this.state.compressionEnabled,
            preset: this.state.selectedPreset,
            medicalContext: this.options.medicalContext
        };
    }

    /**
     * Set medical context for auto-configuration
     */
    setMedicalContext(context) {
        this.options.medicalContext = context;
        
        // Auto-configure based on medical priority
        if (context.priority === 'emergency') {
            this.activateEmergencyBypass();
        } else if (context.priority === 'urgent') {
            this.selectPreset('mobile-optimized');
        }
    }

    /**
     * Simple event emitter
     */
    emit(eventName, data = {}) {
        const event = new CustomEvent(`compression:${eventName}`, {
            detail: data
        });
        this.container.dispatchEvent(event);
    }
}

// Export for use
window.CompressionControls = CompressionControls;