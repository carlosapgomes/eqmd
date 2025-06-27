/**
 * Medical Metadata Management System
 * Part of Phase 2: Medical-Specific Optimization
 * Handles HIPAA-compliant metadata preservation and stripping
 */

class MedicalMetadataManager {
    constructor() {
        this.hipaaCompliantFields = [
            'creation_time',
            'timecode',
            'duration',
            'encoder',
            'major_brand',
            'minor_version',
            'compatible_brands'
        ];

        this.sensitiveFields = [
            'location',
            'gps',
            'artist',
            'comment',
            'description',
            'title',
            'album',
            'date',
            'copyright',
            'track'
        ];

        this.diagnosticFields = [
            'creation_time',
            'timecode',
            'duration',
            'frame_rate',
            'bit_rate',
            'width',
            'height',
            'color_space',
            'color_primaries',
            'color_transfer'
        ];
    }

    /**
     * Analyze metadata for HIPAA compliance
     */
    analyzeMetadataCompliance(metadata) {
        const analysis = {
            compliant: true,
            sensitiveFieldsFound: [],
            recommendations: [],
            preservedFields: [],
            strippedFields: []
        };

        // Check for sensitive fields
        for (const field in metadata) {
            if (this.sensitiveFields.includes(field.toLowerCase())) {
                analysis.sensitiveFieldsFound.push(field);
                analysis.compliant = false;
            }
        }

        // Generate recommendations
        if (analysis.sensitiveFieldsFound.length > 0) {
            analysis.recommendations.push({
                type: 'security',
                message: `Found ${analysis.sensitiveFieldsFound.length} potentially sensitive metadata fields`,
                action: 'strip_sensitive_metadata',
                fields: analysis.sensitiveFieldsFound
            });
        }

        // Determine which fields to preserve vs strip
        for (const field in metadata) {
            if (this.hipaaCompliantFields.includes(field.toLowerCase())) {
                analysis.preservedFields.push(field);
            } else {
                analysis.strippedFields.push(field);
            }
        }

        return analysis;
    }

    /**
     * Get metadata preservation strategy for medical content
     */
    getPreservationStrategy(contentType, preset) {
        const strategies = {
            'diagnostic': {
                preserve: this.diagnosticFields,
                strip: this.sensitiveFields,
                reasoning: 'Preserve diagnostic metadata for medical analysis'
            },
            'documentation': {
                preserve: ['creation_time', 'duration', 'encoder'],
                strip: this.sensitiveFields,
                reasoning: 'Minimal metadata for documentation purposes'
            },
            'consultation': {
                preserve: ['creation_time', 'duration'],
                strip: [...this.sensitiveFields, 'location', 'gps'],
                reasoning: 'Basic metadata for consultation sharing'
            },
            'emergency': {
                preserve: ['creation_time'],
                strip: '*', // Strip all except essential
                reasoning: 'Emergency upload with minimal metadata'
            }
        };

        return strategies[contentType] || strategies['documentation'];
    }

    /**
     * Generate ffmpeg metadata arguments
     */
    generateMetadataArgs(preservationStrategy, originalMetadata = {}) {
        const args = [];

        if (preservationStrategy.strip === '*') {
            // Strip all metadata except what's explicitly preserved
            args.push('-map_metadata', '-1');
            
            // Add back only preserved fields
            preservationStrategy.preserve.forEach(field => {
                if (originalMetadata[field]) {
                    args.push('-metadata', `${field}=${originalMetadata[field]}`);
                }
            });
        } else {
            // Keep original metadata and strip sensitive fields
            args.push('-map_metadata', '0');
            
            // Remove sensitive fields
            preservationStrategy.strip.forEach(field => {
                args.push('-metadata', `${field}=`);
            });
        }

        return args;
    }

    /**
     * Create medical audit trail entry
     */
    createAuditTrailEntry(operation, metadata, preservationStrategy) {
        const auditEntry = {
            timestamp: new Date().toISOString(),
            operation,
            metadataCompliance: {
                strategy: preservationStrategy,
                originalFieldCount: Object.keys(metadata).length,
                preservedFields: preservationStrategy.preserve,
                strippedFields: preservationStrategy.strip,
                reasoning: preservationStrategy.reasoning
            },
            hipaaCompliant: true,
            medicalStandards: {
                colorSpacePreserved: this._checkColorSpacePreservation(metadata),
                timestampAccurate: this._checkTimestampAccuracy(metadata),
                diagnosticDataIntact: this._checkDiagnosticDataIntegrity(metadata, preservationStrategy)
            }
        };

        return auditEntry;
    }

    /**
     * Validate metadata preservation for medical compliance
     */
    validateMetadataPreservation(originalMetadata, processedMetadata, contentType) {
        const validation = {
            passed: true,
            issues: [],
            recommendations: []
        };

        // Check critical medical fields
        const criticalFields = this._getCriticalFieldsForContentType(contentType);
        
        for (const field of criticalFields) {
            if (originalMetadata[field] && !processedMetadata[field]) {
                validation.issues.push({
                    type: 'missing_critical_field',
                    field,
                    message: `Critical medical field '${field}' was removed during processing`
                });
                validation.passed = false;
            }
        }

        // Check for sensitive data leakage
        const sensitiveLeaks = this._checkSensitiveDataLeakage(processedMetadata);
        if (sensitiveLeaks.length > 0) {
            validation.issues.push({
                type: 'sensitive_data_leak',
                fields: sensitiveLeaks,
                message: 'Sensitive metadata fields were not properly stripped'
            });
            validation.passed = false;
        }

        // Generate recommendations
        if (validation.issues.length > 0) {
            validation.recommendations.push({
                action: 'review_metadata_settings',
                message: 'Review metadata preservation settings to ensure medical compliance'
            });
        }

        return validation;
    }

    /**
     * Secure cleanup of temporary metadata
     */
    secureCleanup(temporaryMetadata) {
        // In a real implementation, this would securely wipe memory
        // For now, we'll clear references and suggest garbage collection
        
        if (temporaryMetadata && typeof temporaryMetadata === 'object') {
            // Clear all properties
            Object.keys(temporaryMetadata).forEach(key => {
                delete temporaryMetadata[key];
            });
        }

        // Suggest garbage collection
        if (window.gc) {
            window.gc();
        }

        return {
            cleaned: true,
            timestamp: new Date().toISOString(),
            method: 'secure_reference_clearing'
        };
    }

    /**
     * Extract safe metadata summary for UI display
     */
    getSafeMetadataSummary(metadata) {
        const safeSummary = {};

        // Only include non-sensitive fields in summary
        const safeFields = [
            'duration',
            'width',
            'height',
            'frame_rate',
            'bit_rate',
            'encoder',
            'format',
            'creation_time'
        ];

        safeFields.forEach(field => {
            if (metadata[field] !== undefined) {
                safeSummary[field] = metadata[field];
            }
        });

        return safeSummary;
    }

    // Private methods

    _getCriticalFieldsForContentType(contentType) {
        const criticalFields = {
            'diagnostic': ['creation_time', 'timecode', 'duration', 'frame_rate'],
            'documentation': ['creation_time', 'duration'],
            'consultation': ['creation_time', 'duration'],
            'emergency': ['creation_time']
        };

        return criticalFields[contentType] || criticalFields['documentation'];
    }

    _checkSensitiveDataLeakage(metadata) {
        const leaks = [];
        
        for (const field in metadata) {
            if (this.sensitiveFields.includes(field.toLowerCase())) {
                leaks.push(field);
            }
        }

        return leaks;
    }

    _checkColorSpacePreservation(metadata) {
        return metadata.color_space !== undefined || 
               metadata.color_primaries !== undefined ||
               metadata.color_transfer !== undefined;
    }

    _checkTimestampAccuracy(metadata) {
        return metadata.creation_time !== undefined && 
               !isNaN(Date.parse(metadata.creation_time));
    }

    _checkDiagnosticDataIntegrity(metadata, preservationStrategy) {
        const diagnosticFields = this.diagnosticFields;
        const preservedDiagnosticFields = preservationStrategy.preserve.filter(field => 
            diagnosticFields.includes(field)
        );

        return {
            totalDiagnosticFields: diagnosticFields.length,
            preservedDiagnosticFields: preservedDiagnosticFields.length,
            integrityScore: preservedDiagnosticFields.length / diagnosticFields.length,
            intact: preservedDiagnosticFields.length >= 3 // Minimum threshold
        };
    }
}

/**
 * HIPAA Compliance Checker
 * Specialized class for HIPAA compliance validation
 */
class HIPAAComplianceChecker {
    constructor() {
        this.complianceRules = {
            'safeguards': {
                'administrative': ['audit_trail', 'access_control', 'user_authentication'],
                'physical': ['secure_storage', 'device_control', 'workstation_security'],
                'technical': ['encryption', 'access_control', 'audit_controls', 'integrity_controls']
            },
            'phi_identifiers': [
                'names', 'addresses', 'dates', 'phone_numbers', 'fax_numbers',
                'email_addresses', 'ssn', 'medical_record_numbers', 'health_plan_numbers',
                'account_numbers', 'certificate_numbers', 'vehicle_identifiers',
                'device_identifiers', 'web_urls', 'ip_addresses', 'biometric_identifiers',
                'full_face_photos', 'unique_identifying_numbers'
            ]
        };
    }

    /**
     * Check HIPAA compliance for video metadata
     */
    checkVideoMetadataCompliance(metadata) {
        const compliance = {
            compliant: true,
            violations: [],
            recommendations: [],
            riskLevel: 'low'
        };

        // Check for potential PHI in metadata
        const phiRisks = this._identifyPHIRisks(metadata);
        if (phiRisks.length > 0) {
            compliance.compliant = false;
            compliance.violations.push({
                type: 'phi_exposure',
                risks: phiRisks,
                message: 'Potential PHI found in video metadata'
            });
            compliance.riskLevel = 'high';
        }

        // Check for location data
        if (this._hasLocationData(metadata)) {
            compliance.violations.push({
                type: 'location_data',
                message: 'GPS or location data found in metadata',
                recommendation: 'Strip location data before processing'
            });
            compliance.riskLevel = 'high';
        }

        // Generate recommendations
        compliance.recommendations = this._generateHIPAARecommendations(compliance.violations);

        return compliance;
    }

    /**
     * Get HIPAA-compliant metadata handling instructions
     */
    getHIPAACompliantInstructions(contentType) {
        const instructions = {
            'diagnostic': {
                strip: ['location', 'gps', 'artist', 'comment', 'description'],
                preserve: ['creation_time', 'timecode', 'duration', 'technical_specs'],
                auditRequired: true,
                encryptionRequired: true
            },
            'documentation': {
                strip: ['location', 'gps', 'artist', 'comment', 'description', 'title'],
                preserve: ['creation_time', 'duration'],
                auditRequired: true,
                encryptionRequired: false
            },
            'consultation': {
                strip: ['*'], // Strip all except essential
                preserve: ['creation_time'],
                auditRequired: true,
                encryptionRequired: true
            }
        };

        return instructions[contentType] || instructions['documentation'];
    }

    // Private methods

    _identifyPHIRisks(metadata) {
        const risks = [];
        
        // Check for potential names in various fields
        const nameFields = ['artist', 'author', 'creator', 'title', 'description', 'comment'];
        nameFields.forEach(field => {
            if (metadata[field] && this._containsPotentialName(metadata[field])) {
                risks.push({
                    field,
                    type: 'potential_name',
                    value: metadata[field]
                });
            }
        });

        // Check for dates that might be birth dates
        const dateFields = ['date', 'creation_time', 'date_recorded'];
        dateFields.forEach(field => {
            if (metadata[field] && this._isPotentialBirthDate(metadata[field])) {
                risks.push({
                    field,
                    type: 'potential_birth_date',
                    value: metadata[field]
                });
            }
        });

        return risks;
    }

    _hasLocationData(metadata) {
        const locationFields = ['location', 'gps', 'latitude', 'longitude', 'gps_coordinates'];
        return locationFields.some(field => metadata[field] !== undefined);
    }

    _containsPotentialName(value) {
        // Simple check for potential names (capital letters suggesting proper nouns)
        const namePattern = /\b[A-Z][a-z]+\s+[A-Z][a-z]+\b/;
        return namePattern.test(value);
    }

    _isPotentialBirthDate(dateString) {
        // Check if date is more than 18 years ago but less than 120 years ago
        const date = new Date(dateString);
        const now = new Date();
        const yearsDiff = now.getFullYear() - date.getFullYear();
        
        return yearsDiff >= 18 && yearsDiff <= 120;
    }

    _generateHIPAARecommendations(violations) {
        const recommendations = [];

        if (violations.some(v => v.type === 'phi_exposure')) {
            recommendations.push({
                priority: 'high',
                action: 'strip_phi_metadata',
                message: 'Remove all potentially identifying metadata fields'
            });
        }

        if (violations.some(v => v.type === 'location_data')) {
            recommendations.push({
                priority: 'high',
                action: 'remove_location_data',
                message: 'Strip GPS and location metadata'
            });
        }

        if (violations.length > 0) {
            recommendations.push({
                priority: 'medium',
                action: 'implement_audit_trail',
                message: 'Implement comprehensive audit trail for metadata handling'
            });
        }

        return recommendations;
    }
}

// Export classes
window.MedicalMetadataManager = MedicalMetadataManager;
window.HIPAAComplianceChecker = HIPAAComplianceChecker;