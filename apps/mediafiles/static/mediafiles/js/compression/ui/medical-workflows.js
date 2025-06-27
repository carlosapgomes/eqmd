/**
 * Medical Workflow UI Components
 * Part of Phase 2: Medical-Specific Optimization
 * Provides medical-focused user interface for video compression
 */

class MedicalCompressionUI {
    constructor(containerElement, compressionManager) {
        this.container = containerElement;
        this.compressionManager = compressionManager;
        this.presetManager = new MedicalPresetManager();
        this.qualityValidator = new MedicalQualityValidator();
        this.metadataManager = new MedicalMetadataManager();
        
        this.currentFile = null;
        this.selectedPreset = null;
        this.contentType = 'documentation'; // Default content type
        this.compressionInProgress = false;
        
        this.elements = {};
        this.init();
    }

    /**
     * Initialize the medical compression UI
     */
    init() {
        this.createUI();
        this.bindEvents();
        this.updateDeviceCapabilities();
    }

    /**
     * Create the medical-focused UI elements
     */
    createUI() {
        const uiHTML = `
            <div class="medical-compression-panel" style="display: none;">
                <div class="compression-header">
                    <h6 class="mb-3">
                        <i class="fas fa-compress-alt text-primary"></i>
                        Compressão de Vídeo Médico
                    </h6>
                    <div class="compression-toggle">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="enableCompression">
                            <label class="form-check-label" for="enableCompression">
                                Ativar compressão
                            </label>
                        </div>
                    </div>
                </div>

                <div class="compression-options" style="display: none;">
                    <!-- Content Type Selection -->
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Tipo de Conteúdo</label>
                            <select class="form-select" id="contentType">
                                <option value="documentation">Documentação Geral</option>
                                <option value="diagnostic">Diagnóstico</option>
                                <option value="consultation">Consulta</option>
                                <option value="emergency">Emergência</option>
                            </select>
                            <div class="form-text">
                                <span id="contentTypeHelp">Documentação médica padrão</span>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Qualidade</label>
                            <select class="form-select" id="qualityPreset">
                                <!-- Options populated dynamically -->
                            </select>
                            <div class="form-text">
                                <span id="qualityHelp">Carregando presets...</span>
                            </div>
                        </div>
                    </div>

                    <!-- Compression Estimates -->
                    <div class="compression-estimates mb-3" style="display: none;">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="estimate-card">
                                    <div class="estimate-label">Tempo Estimado</div>
                                    <div class="estimate-value" id="estimatedTime">-</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="estimate-card">
                                    <div class="estimate-label">Redução de Tamanho</div>
                                    <div class="estimate-value" id="sizeReduction">-</div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="estimate-card">
                                    <div class="estimate-label">Qualidade</div>
                                    <div class="estimate-value" id="qualityScore">-</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Medical Compliance Info -->
                    <div class="compliance-info">
                        <div class="alert alert-info alert-sm">
                            <i class="fas fa-shield-alt"></i>
                            <strong>Conformidade Médica:</strong>
                            <span id="complianceStatus">Verificando...</span>
                        </div>
                    </div>

                    <!-- Emergency Bypass -->
                    <div class="emergency-bypass">
                        <button type="button" class="btn btn-link btn-sm text-danger" id="emergencyBypass">
                            <i class="fas fa-exclamation-triangle"></i>
                            Pular compressão (Emergência)
                        </button>
                    </div>
                </div>

                <!-- Compression Progress -->
                <div class="compression-progress" style="display: none;">
                    <div class="progress-header">
                        <h6>Comprimindo vídeo...</h6>
                        <button type="button" class="btn btn-sm btn-outline-secondary" id="cancelCompression">
                            Cancelar
                        </button>
                    </div>
                    <div class="progress mb-2">
                        <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                    </div>
                    <div class="progress-details">
                        <small class="text-muted">
                            <span id="progressStatus">Iniciando...</span>
                            <span class="float-end" id="progressTime">0s</span>
                        </small>
                    </div>
                    <div class="progress-actions mt-2">
                        <button type="button" class="btn btn-sm btn-warning" id="fallbackToDirectUpload" style="display: none;">
                            <i class="fas fa-upload"></i>
                            Enviar sem compressão
                        </button>
                    </div>
                </div>

                <!-- Quality Validation Results -->
                <div class="quality-validation" style="display: none;">
                    <div class="validation-header">
                        <h6>Validação de Qualidade</h6>
                    </div>
                    <div class="validation-results" id="validationResults">
                        <!-- Populated dynamically -->
                    </div>
                </div>
            </div>
        `;

        this.container.insertAdjacentHTML('beforeend', uiHTML);
        this.cacheElements();
    }

    /**
     * Cache UI elements for performance
     */
    cacheElements() {
        this.elements = {
            panel: this.container.querySelector('.medical-compression-panel'),
            toggle: this.container.querySelector('#enableCompression'),
            options: this.container.querySelector('.compression-options'),
            contentType: this.container.querySelector('#contentType'),
            qualityPreset: this.container.querySelector('#qualityPreset'),
            estimates: this.container.querySelector('.compression-estimates'),
            progress: this.container.querySelector('.compression-progress'),
            progressBar: this.container.querySelector('.progress-bar'),
            progressStatus: this.container.querySelector('#progressStatus'),
            progressTime: this.container.querySelector('#progressTime'),
            validation: this.container.querySelector('.quality-validation'),
            emergencyBypass: this.container.querySelector('#emergencyBypass'),
            cancelCompression: this.container.querySelector('#cancelCompression'),
            fallbackUpload: this.container.querySelector('#fallbackToDirectUpload')
        };
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        // Toggle compression
        this.elements.toggle.addEventListener('change', (e) => {
            this.toggleCompression(e.target.checked);
        });

        // Content type change
        this.elements.contentType.addEventListener('change', (e) => {
            this.updateContentType(e.target.value);
        });

        // Quality preset change
        this.elements.qualityPreset.addEventListener('change', (e) => {
            this.updateQualityPreset(e.target.value);
        });

        // Emergency bypass
        this.elements.emergencyBypass.addEventListener('click', () => {
            this.triggerEmergencyBypass();
        });

        // Cancel compression
        this.elements.cancelCompression.addEventListener('click', () => {
            this.cancelCompression();
        });

        // Fallback to direct upload
        this.elements.fallbackUpload.addEventListener('click', () => {
            this.fallbackToDirectUpload();
        });
    }

    /**
     * Show the compression panel for a file
     */
    showForFile(file) {
        this.currentFile = file;
        this.elements.panel.style.display = 'block';
        this.updateEstimates();
        this.checkMedicalCompliance();
    }

    /**
     * Hide the compression panel
     */
    hide() {
        this.elements.panel.style.display = 'none';
        this.currentFile = null;
        this.reset();
    }

    /**
     * Toggle compression on/off
     */
    toggleCompression(enabled) {
        if (enabled) {
            this.elements.options.style.display = 'block';
            this.populateQualityPresets();
        } else {
            this.elements.options.style.display = 'none';
        }
    }

    /**
     * Update content type and adjust presets
     */
    updateContentType(contentType) {
        this.contentType = contentType;
        this.updateContentTypeHelp();
        this.populateQualityPresets();
        this.updateEstimates();
        this.checkMedicalCompliance();
    }

    /**
     * Update quality preset
     */
    updateQualityPreset(preset) {
        this.selectedPreset = preset;
        this.updateQualityHelp();
        this.updateEstimates();
    }

    /**
     * Update device capabilities display
     */
    updateDeviceCapabilities() {
        const capabilities = this.compressionManager.getCapabilities();
        if (!capabilities?.supported) {
            this.elements.panel.style.display = 'none';
            return;
        }

        // Show device compatibility info
        const deviceScore = capabilities.score;
        const deviceClass = this.getDeviceClass(deviceScore);
        
        // Update UI based on device capabilities
        this.updateUIForDeviceClass(deviceClass);
    }

    /**
     * Populate quality presets based on device and content type
     */
    populateQualityPresets() {
        const capabilities = this.compressionManager.getCapabilities();
        const availablePresets = this.presetManager.getPresetsForDevice(capabilities);
        
        // Filter presets based on content type
        const suitablePresets = availablePresets.filter(preset => {
            if (this.contentType === 'diagnostic') {
                return preset.medicalSettings.diagnosticSafe;
            }
            return true;
        });

        // Clear and populate select
        this.elements.qualityPreset.innerHTML = '';
        
        suitablePresets.forEach(preset => {
            const option = document.createElement('option');
            option.value = preset.key;
            option.textContent = preset.name;
            this.elements.qualityPreset.appendChild(option);
        });

        // Select recommended preset
        const recommended = this.qualityValidator.getRecommendedPresetForMedicalContent(
            this.contentType,
            this.currentFile?.size || 0,
            capabilities
        );
        
        if (recommended && this.elements.qualityPreset.querySelector(`option[value="${recommended}"]`)) {
            this.elements.qualityPreset.value = recommended;
            this.selectedPreset = recommended;
        }
    }

    /**
     * Update compression estimates
     */
    updateEstimates() {
        if (!this.currentFile || !this.selectedPreset) {
            this.elements.estimates.style.display = 'none';
            return;
        }

        const estimates = this.compressionManager.estimateCompression(this.currentFile, this.selectedPreset);
        
        // Update estimates display
        this.container.querySelector('#estimatedTime').textContent = `${estimates.estimatedTime}s`;
        this.container.querySelector('#sizeReduction').textContent = `${(estimates.sizeReduction * 100).toFixed(0)}%`;
        
        const qualityScore = this.qualityValidator.getPresetQualityScore(this.selectedPreset);
        this.container.querySelector('#qualityScore').textContent = this.getQualityLabel(qualityScore);
        
        this.elements.estimates.style.display = 'block';
    }

    /**
     * Check medical compliance
     */
    checkMedicalCompliance() {
        const preset = this.presetManager.getPreset(this.selectedPreset);
        if (!preset) return;

        const validation = this.presetManager.validatePresetForMedicalUse(this.selectedPreset, this.contentType);
        const complianceStatus = this.container.querySelector('#complianceStatus');
        
        if (validation.valid) {
            if (validation.warnings.length > 0) {
                complianceStatus.innerHTML = `
                    <span class="text-warning">Conforme com avisos</span>
                    <ul class="mt-1 mb-0">
                        ${validation.warnings.map(w => `<li>${w}</li>`).join('')}
                    </ul>
                `;
            } else {
                complianceStatus.innerHTML = '<span class="text-success">Totalmente conforme</span>';
            }
        } else {
            complianceStatus.innerHTML = `<span class="text-danger">Não conforme: ${validation.reason}</span>`;
        }
    }

    /**
     * Start compression process
     */
    async startCompression() {
        if (!this.currentFile || !this.selectedPreset) {
            throw new Error('File and preset must be selected');
        }

        this.compressionInProgress = true;
        this.showProgressUI();

        try {
            // Setup progress handlers
            this.compressionManager.onProgress = (data) => {
                this.updateProgress(data);
            };

            this.compressionManager.onComplete = (data) => {
                this.handleCompressionComplete(data);
            };

            this.compressionManager.onError = (error) => {
                this.handleCompressionError(error);
            };

            // Start compression
            const compressedFile = await this.compressionManager.compressVideo(this.currentFile, {
                preset: this.selectedPreset,
                contentType: this.contentType
            });

            return compressedFile;

        } catch (error) {
            this.handleCompressionError(error);
            throw error;
        }
    }

    /**
     * Show progress UI
     */
    showProgressUI() {
        this.elements.options.style.display = 'none';
        this.elements.progress.style.display = 'block';
        this.startProgressTimer();
    }

    /**
     * Update compression progress
     */
    updateProgress(data) {
        const percentage = Math.round(data.progress * 100);
        this.elements.progressBar.style.width = `${percentage}%`;
        this.elements.progressBar.textContent = `${percentage}%`;
        
        if (data.stage) {
            this.elements.progressStatus.textContent = this.getProgressMessage(data.stage);
        }
    }

    /**
     * Handle compression completion
     */
    async handleCompressionComplete(data) {
        this.compressionInProgress = false;
        this.hideProgressUI();

        // Validate compressed file quality
        const validation = await this.qualityValidator.validateCompressedVideo(
            this.currentFile,
            data.compressedFile,
            this.selectedPreset
        );

        this.showValidationResults(validation);
        
        if (validation.passed) {
            // Compression successful and validated
            this.triggerCompressionSuccess(data.compressedFile, validation);
        } else {
            // Quality validation failed
            this.showQualityWarnings(validation);
        }
    }

    /**
     * Handle compression error
     */
    handleCompressionError(error) {
        this.compressionInProgress = false;
        this.hideProgressUI();
        
        // Show fallback option
        this.elements.fallbackUpload.style.display = 'block';
        
        // Show error message
        this.showErrorMessage(error.message);
    }

    /**
     * Trigger emergency bypass
     */
    triggerEmergencyBypass() {
        const confirmed = confirm(
            'Tem certeza que deseja pular a compressão?\n\n' +
            'O arquivo será enviado sem compressão, o que pode resultar em upload mais lento.'
        );
        
        if (confirmed) {
            this.triggerDirectUpload();
        }
    }

    /**
     * Cancel compression
     */
    cancelCompression() {
        if (this.compressionInProgress) {
            this.compressionManager.cancelCompression();
            this.compressionInProgress = false;
            this.hideProgressUI();
            this.elements.options.style.display = 'block';
        }
    }

    /**
     * Fallback to direct upload
     */
    fallbackToDirectUpload() {
        this.triggerDirectUpload();
    }

    /**
     * Reset UI state
     */
    reset() {
        this.compressionInProgress = false;
        this.elements.options.style.display = 'none';
        this.elements.progress.style.display = 'none';
        this.elements.validation.style.display = 'none';
        this.elements.toggle.checked = false;
        this.clearProgressTimer();
    }

    // Helper methods

    getDeviceClass(score) {
        if (score >= 80) return 'high-end';
        if (score >= 60) return 'mid-range';
        return 'low-end';
    }

    updateUIForDeviceClass(deviceClass) {
        const panel = this.elements.panel;
        panel.classList.remove('device-high-end', 'device-mid-range', 'device-low-end');
        panel.classList.add(`device-${deviceClass}`);
    }

    updateContentTypeHelp() {
        const helpText = {
            'documentation': 'Documentação médica padrão',
            'diagnostic': 'Conteúdo para diagnóstico - máxima qualidade',
            'consultation': 'Compartilhamento para consulta',
            'emergency': 'Upload rápido para emergências'
        };
        
        this.container.querySelector('#contentTypeHelp').textContent = helpText[this.contentType];
    }

    updateQualityHelp() {
        const preset = this.presetManager.getPreset(this.selectedPreset);
        if (preset) {
            this.container.querySelector('#qualityHelp').textContent = preset.description;
        }
    }

    getQualityLabel(score) {
        if (score >= 0.9) return 'Excelente';
        if (score >= 0.8) return 'Muito Boa';
        if (score >= 0.7) return 'Boa';
        if (score >= 0.6) return 'Adequada';
        return 'Básica';
    }

    getProgressMessage(stage) {
        const messages = {
            'analyzing': 'Analisando arquivo...',
            'compressing': 'Comprimindo vídeo...',
            'finalizing': 'Finalizando...',
            'validating': 'Validando qualidade...'
        };
        
        return messages[stage] || 'Processando...';
    }

    startProgressTimer() {
        this.progressStartTime = Date.now();
        this.progressTimer = setInterval(() => {
            const elapsed = Math.round((Date.now() - this.progressStartTime) / 1000);
            this.elements.progressTime.textContent = `${elapsed}s`;
        }, 1000);
    }

    clearProgressTimer() {
        if (this.progressTimer) {
            clearInterval(this.progressTimer);
            this.progressTimer = null;
        }
    }

    hideProgressUI() {
        this.elements.progress.style.display = 'none';
        this.elements.fallbackUpload.style.display = 'none';
        this.clearProgressTimer();
    }

    showValidationResults(validation) {
        this.elements.validation.style.display = 'block';
        const resultsContainer = this.container.querySelector('#validationResults');
        
        let html = '';
        
        if (validation.passed) {
            html += '<div class="alert alert-success alert-sm">Qualidade validada com sucesso!</div>';
        } else {
            html += '<div class="alert alert-warning alert-sm">Avisos de qualidade encontrados</div>';
        }
        
        if (validation.warnings.length > 0) {
            html += '<div class="mt-2"><strong>Avisos:</strong><ul>';
            validation.warnings.forEach(warning => {
                html += `<li>${warning.message}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (validation.recommendations.length > 0) {
            html += '<div class="mt-2"><strong>Recomendações:</strong><ul>';
            validation.recommendations.forEach(rec => {
                html += `<li>${rec}</li>`;
            });
            html += '</ul></div>';
        }
        
        resultsContainer.innerHTML = html;
    }

    showQualityWarnings(validation) {
        // Show quality warnings but allow user to proceed
        const proceed = confirm(
            'Avisos de qualidade detectados:\n\n' +
            validation.warnings.map(w => `• ${w.message}`).join('\n') +
            '\n\nDeseja continuar com o arquivo comprimido?'
        );
        
        if (proceed) {
            this.triggerCompressionSuccess(null, validation);
        } else {
            this.elements.options.style.display = 'block';
        }
    }

    showErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-sm';
        errorDiv.innerHTML = `<strong>Erro na compressão:</strong> ${message}`;
        
        this.elements.progress.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    triggerCompressionSuccess(compressedFile, validation) {
        // Trigger custom event for parent components
        const event = new CustomEvent('compressionComplete', {
            detail: {
                originalFile: this.currentFile,
                compressedFile,
                validation,
                preset: this.selectedPreset,
                contentType: this.contentType
            }
        });
        
        this.container.dispatchEvent(event);
    }

    triggerDirectUpload() {
        // Trigger custom event for direct upload
        const event = new CustomEvent('directUpload', {
            detail: {
                file: this.currentFile,
                reason: 'compression_bypassed'
            }
        });
        
        this.container.dispatchEvent(event);
    }
}

// Export class
window.MedicalCompressionUI = MedicalCompressionUI;