/**
 * MedicalContextDetector - Detect and configure medical context for compression
 */
class MedicalContextDetector {
    constructor() {
        this.context = this.detectContext();
    }

    /**
     * Detect medical context from page
     */
    detectContext() {
        const urlPath = window.location.pathname;
        const patientElement = document.querySelector('[data-patient-id]');
        
        return {
            patientId: patientElement?.dataset.patientId,
            priority: this.detectPriority(),
            specialty: this.detectSpecialty(),
            emergencyCase: this.isEmergencyCase(),
            workflowStep: this.detectWorkflowStep()
        };
    }

    /**
     * Detect medical priority
     */
    detectPriority() {
        // Check URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('emergency')) return 'emergency';
        if (urlParams.has('urgent')) return 'urgent';

        // Check page elements
        const priorityIndicators = {
            'emergency': ['.emergency-case', '.priority-emergency', '[data-emergency="true"]'],
            'urgent': ['.urgent-case', '.priority-urgent', '[data-urgent="true"]'],
            'routine': ['.routine-case', '.priority-routine']
        };

        for (const [priority, selectors] of Object.entries(priorityIndicators)) {
            if (selectors.some(selector => document.querySelector(selector))) {
                return priority;
            }
        }

        return 'routine';
    }

    /**
     * Detect medical specialty
     */
    detectSpecialty() {
        const specialtyElement = document.querySelector('[data-specialty]');
        return specialtyElement?.dataset.specialty || 'general';
    }

    /**
     * Check if this is an emergency case
     */
    isEmergencyCase() {
        return this.context?.priority === 'emergency' || 
               document.querySelector('.emergency-case') !== null;
    }

    /**
     * Detect workflow step
     */
    detectWorkflowStep() {
        const pathname = window.location.pathname;
        
        if (pathname.includes('/create/')) return 'initial_documentation';
        if (pathname.includes('/edit/')) return 'update_documentation';
        if (pathname.includes('/emergency/')) return 'emergency_documentation';
        
        return 'documentation';
    }

    /**
     * Get compression recommendations based on context
     */
    getCompressionRecommendations() {
        const recommendations = {
            emergency: {
                enabled: false,
                reason: 'Emergency cases require immediate upload',
                preset: null,
                showEmergencyBypass: true
            },
            urgent: {
                enabled: true,
                reason: 'Quick compression recommended for urgent cases',
                preset: 'mobile-optimized',
                timeout: 30000
            },
            routine: {
                enabled: true,
                reason: 'Standard compression for optimal file size',
                preset: 'medical-standard',
                timeout: 60000
            }
        };

        return recommendations[this.context.priority] || recommendations.routine;
    }

    /**
     * Configure compression controls based on medical context
     */
    configureCompressionControls(compressionControls) {
        const recommendations = this.getCompressionRecommendations();
        
        // Set medical context
        compressionControls.setMedicalContext(this.context);
        
        // Auto-configure based on recommendations
        if (!recommendations.enabled) {
            compressionControls.activateEmergencyBypass();
        } else if (recommendations.preset) {
            compressionControls.selectPreset(recommendations.preset);
        }
        
        return recommendations;
    }
}

// Export for use
window.MedicalContextDetector = MedicalContextDetector;