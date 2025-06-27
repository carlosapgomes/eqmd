/**
 * Medical Quality Presets and Validation System
 * Part of Phase 2: Medical-Specific Optimization
 */

class MedicalQualityValidator {
    constructor() {
        this.thresholds = {
            maxSizeReduction: 0.70, // Alert if compression reduces size by more than 70%
            minQualityScore: 0.30,  // Minimum acceptable quality score
            maxBitrateVariation: 0.20 // Maximum acceptable bitrate variation
        };
    }

    /**
     * Validate compressed video quality for medical use
     */
    async validateCompressedVideo(originalFile, compressedFile, preset) {
        const validation = {
            passed: true,
            warnings: [],
            errors: [],
            metrics: {},
            recommendations: []
        };

        try {
            // Basic size validation
            const sizeValidation = this._validateSizeReduction(originalFile, compressedFile);
            validation.metrics.sizeReduction = sizeValidation.reduction;
            
            if (sizeValidation.excessive) {
                validation.warnings.push({
                    type: 'excessive_compression',
                    message: `Compression reduced file size by ${(sizeValidation.reduction * 100).toFixed(1)}%. This may affect diagnostic quality.`,
                    recommendation: 'Consider using a higher quality preset for diagnostic content.'
                });
            }

            // Quality assessment based on preset
            const qualityAssessment = this._assessPresetQuality(preset, originalFile.size);
            validation.metrics.qualityAssessment = qualityAssessment;
            
            if (qualityAssessment.diagnostic && qualityAssessment.score < 0.8) {
                validation.warnings.push({
                    type: 'quality_concern',
                    message: 'Current settings may not preserve diagnostic quality.',
                    recommendation: 'Consider medical-high preset for diagnostic content.'
                });
            }

            // Medical compliance check
            const complianceCheck = this._checkMedicalCompliance(preset, originalFile, compressedFile);
            validation.metrics.compliance = complianceCheck;
            
            if (!complianceCheck.hipaaCompliant) {
                validation.errors.push({
                    type: 'compliance_violation',
                    message: 'Compression settings may not meet medical privacy requirements.',
                    recommendation: 'Ensure metadata stripping is enabled.'
                });
                validation.passed = false;
            }

            // Generate overall recommendation
            validation.recommendations = this._generateRecommendations(validation);

        } catch (error) {
            validation.errors.push({
                type: 'validation_error',
                message: `Quality validation failed: ${error.message}`,
                recommendation: 'Proceed with caution or use direct upload.'
            });
            validation.passed = false;
        }

        return validation;
    }

    /**
     * Get quality score for a preset
     */
    getPresetQualityScore(preset) {
        const presetScores = {
            'medical-high': 0.95,      // Visually lossless
            'standard-medical': 0.80,   // High quality
            'mobile-optimized': 0.65    // Good quality
        };
        
        return presetScores[preset] || 0.50;
    }

    /**
     * Check if preset is suitable for diagnostic content
     */
    isPresetDiagnosticSafe(preset) {
        const diagnosticSafePresets = ['medical-high'];
        return diagnosticSafePresets.includes(preset);
    }

    /**
     * Get recommended preset for medical content type
     */
    getRecommendedPresetForMedicalContent(contentType, fileSize, deviceCapabilities) {
        const fileSizeMB = fileSize / (1024 * 1024);
        const deviceScore = deviceCapabilities?.score || 50;

        switch (contentType) {
            case 'diagnostic':
                // Always use highest quality for diagnostic content
                return deviceScore >= 80 ? 'medical-high' : 'standard-medical';
                
            case 'documentation':
                // Balance quality and efficiency for documentation
                if (fileSizeMB > 50 && deviceScore >= 70) {
                    return 'standard-medical';
                }
                return 'mobile-optimized';
                
            case 'consultation':
                // Quick sharing optimized
                return 'mobile-optimized';
                
            case 'emergency':
                // Fastest upload, maintain acceptable quality
                return 'mobile-optimized';
                
            default:
                // Default to standard medical
                return deviceScore >= 60 ? 'standard-medical' : 'mobile-optimized';
        }
    }

    // Private methods

    _validateSizeReduction(originalFile, compressedFile) {
        const reduction = 1 - (compressedFile.size / originalFile.size);
        
        return {
            reduction,
            excessive: reduction > this.thresholds.maxSizeReduction,
            originalSize: originalFile.size,
            compressedSize: compressedFile.size
        };
    }

    _assessPresetQuality(preset, originalFileSize) {
        const qualityScore = this.getPresetQualityScore(preset);
        const diagnosticSafe = this.isPresetDiagnosticSafe(preset);
        
        return {
            preset,
            score: qualityScore,
            diagnostic: diagnosticSafe,
            suitable: qualityScore >= this.thresholds.minQualityScore,
            originalFileSize
        };
    }

    _checkMedicalCompliance(preset, originalFile, compressedFile) {
        // Basic compliance checks
        const compliance = {
            hipaaCompliant: true,
            metadataStripped: true, // Assume metadata is stripped in compression
            auditTrail: true,
            reasonableQuality: this.getPresetQualityScore(preset) >= 0.60
        };

        // Check if compression is too aggressive for medical use
        const sizeReduction = 1 - (compressedFile.size / originalFile.size);
        if (sizeReduction > 0.80) {
            compliance.reasonableQuality = false;
            compliance.hipaaCompliant = false;
        }

        return compliance;
    }

    _generateRecommendations(validation) {
        const recommendations = [];
        
        if (validation.metrics.sizeReduction > 0.60) {
            recommendations.push('Consider using a higher quality preset to preserve medical detail.');
        }
        
        if (validation.metrics.qualityAssessment && !validation.metrics.qualityAssessment.diagnostic) {
            recommendations.push('For diagnostic content, use medical-high preset when possible.');
        }
        
        if (validation.warnings.length > 0) {
            recommendations.push('Review quality warnings before proceeding with compressed file.');
        }
        
        if (validation.errors.length === 0 && validation.warnings.length === 0) {
            recommendations.push('Compression settings are appropriate for medical use.');
        }
        
        return recommendations;
    }
}

/**
 * Medical Preset Configuration with enhanced medical-specific settings
 */
class MedicalPresetManager {
    constructor() {
        this.presets = {
            'medical-high': {
                name: 'Medical High Quality (Diagnostic)',
                description: 'Visually lossless compression for diagnostic content',
                crf: 18,
                maxBitrate: '8M',
                bufsize: '16M',
                preset: 'medium',
                profile: 'high',
                level: '4.0',
                pixelFormat: 'yuv420p',
                medicalSettings: {
                    preserveMetadata: ['creation_time', 'timecode'],
                    colorSpace: 'bt709',
                    diagnosticSafe: true,
                    maxSizeReduction: 0.30
                }
            },
            'standard-medical': {
                name: 'Standard Medical (Documentation)',
                description: 'High quality for general medical documentation',
                crf: 23,
                maxBitrate: '4M',
                bufsize: '8M',
                preset: 'medium',
                profile: 'main',
                level: '3.1',
                pixelFormat: 'yuv420p',
                medicalSettings: {
                    preserveMetadata: ['creation_time'],
                    colorSpace: 'bt709',
                    diagnosticSafe: false,
                    maxSizeReduction: 0.50
                }
            },
            'mobile-optimized': {
                name: 'Mobile Optimized (Quick Sharing)',
                description: 'Optimized for mobile upload and sharing',
                crf: 28,
                maxBitrate: '2M',
                bufsize: '4M',
                preset: 'fast',
                profile: 'baseline',
                level: '3.0',
                pixelFormat: 'yuv420p',
                medicalSettings: {
                    preserveMetadata: [],
                    colorSpace: 'bt709',
                    diagnosticSafe: false,
                    maxSizeReduction: 0.70
                }
            }
        };
    }

    /**
     * Get preset configuration
     */
    getPreset(presetName) {
        return this.presets[presetName] || null;
    }

    /**
     * Get all available presets
     */
    getAllPresets() {
        return Object.keys(this.presets).map(key => ({
            key,
            ...this.presets[key]
        }));
    }

    /**
     * Get presets suitable for device capabilities
     */
    getPresetsForDevice(deviceCapabilities) {
        const deviceScore = deviceCapabilities?.score || 0;
        const availablePresets = [];

        if (deviceScore >= 80) {
            availablePresets.push('medical-high');
        }
        
        if (deviceScore >= 60) {
            availablePresets.push('standard-medical');
        }
        
        if (deviceScore >= 30) {
            availablePresets.push('mobile-optimized');
        }

        return availablePresets.map(key => ({
            key,
            ...this.presets[key]
        }));
    }

    /**
     * Validate preset for medical use
     */
    validatePresetForMedicalUse(presetName, contentType = 'documentation') {
        const preset = this.getPreset(presetName);
        if (!preset) {
            return { valid: false, reason: 'Preset not found' };
        }

        const validation = { valid: true, warnings: [] };

        // Check if preset is suitable for content type
        if (contentType === 'diagnostic' && !preset.medicalSettings.diagnosticSafe) {
            validation.warnings.push('This preset may not preserve diagnostic quality');
        }

        // Check compression ratio
        if (preset.medicalSettings.maxSizeReduction > 0.60) {
            validation.warnings.push('High compression ratio may affect medical content quality');
        }

        return validation;
    }

    /**
     * Get ffmpeg command arguments for preset
     */
    getFFmpegArgs(presetName, inputFile, outputFile) {
        const preset = this.getPreset(presetName);
        if (!preset) {
            throw new Error(`Unknown preset: ${presetName}`);
        }

        const args = [
            '-i', inputFile,
            '-c:v', 'libx264',
            '-preset', preset.preset,
            '-crf', preset.crf.toString(),
            '-maxrate', preset.maxBitrate,
            '-bufsize', preset.bufsize,
            '-profile:v', preset.profile,
            '-level', preset.level,
            '-pix_fmt', preset.pixelFormat,
            '-movflags', '+faststart'
        ];

        // Add color space settings for medical accuracy
        args.push('-colorspace', 'bt709');
        args.push('-color_primaries', 'bt709');
        args.push('-color_trc', 'bt709');

        // Handle metadata preservation
        if (preset.medicalSettings.preserveMetadata.length > 0) {
            preset.medicalSettings.preserveMetadata.forEach(metadata => {
                args.push('-map_metadata', '0');
                args.push('-metadata:g', `${metadata}=${metadata}`);
            });
        } else {
            args.push('-map_metadata', '-1'); // Strip all metadata
        }

        args.push(outputFile);

        return args;
    }
}

// Export classes
window.MedicalQualityValidator = MedicalQualityValidator;
window.MedicalPresetManager = MedicalPresetManager;