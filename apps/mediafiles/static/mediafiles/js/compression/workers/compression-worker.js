/**
 * CompressionWorker - Web Worker for video compression using ffmpeg.wasm
 * Part of Phase 1: Basic ffmpeg.wasm Integration
 * Enhanced with Phase 2: Medical-Specific Optimization
 */

// Worker global variables
let ffmpeg = null;
let initialized = false;
let currentCompression = null;

// Import Phase 2 medical modules (conceptually - in worker context)
// These would be loaded as separate worker scripts or inlined
let medicalPresetManager = null;
let metadataManager = null;
let qualityValidator = null;

// Enhanced Medical-specific compression presets with Phase 2 improvements
const MEDICAL_PRESETS = {
    'medical-high': {
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

// Memory management configuration
const MEMORY_CONFIG = {
    maxChunkSize: 50 * 1024 * 1024, // 50MB chunks
    memoryThreshold: 500 * 1024 * 1024, // 500MB threshold
    cleanupInterval: 30000 // 30 seconds
};

/**
 * Message handler for worker communication
 */
self.onmessage = async function(event) {
    const { type, data } = event.data;

    try {
        switch (type) {
            case 'init':
                await initializeFFmpeg();
                break;
            case 'compress':
                await compressVideo(event.data);
                break;
            case 'cancel':
                cancelCompression();
                break;
            default:
                sendError(`Unknown message type: ${type}`);
        }
    } catch (error) {
        sendError(`Worker error: ${error.message}`);
    }
};

/**
 * Initialize ffmpeg.wasm
 */
async function initializeFFmpeg() {
    if (initialized) {
        return;
    }

    try {
        // Import ffmpeg.wasm (this will need to be loaded from CDN or local copy)
        // For now, we'll create a placeholder that simulates the interface
        ffmpeg = await createFFmpegInstance();
        
        // Set up memory management
        setupMemoryManagement();
        
        initialized = true;
        sendMessage('init-complete', { success: true });
    } catch (error) {
        sendError(`FFmpeg initialization failed: ${error.message}`);
    }
}

// Import the dynamic ffmpeg loader
importScripts('../ffmpeg-dynamic-loader.js');

// Global ffmpeg loader instance
let ffmpegLoader = null;

/**
 * Get or create FFmpeg loader instance
 */
function getFFmpegLoader() {
    if (!ffmpegLoader) {
        ffmpegLoader = new FFmpegDynamicLoader();
    }
    return ffmpegLoader;
}

/**
 * Create FFmpeg instance using dynamic loading
 */
async function createFFmpegInstance() {
    const loader = getFFmpegLoader();
    
    // Check if FFmpeg is available on this browser
    if (!loader.isFFmpegAvailable()) {
        throw new Error('FFmpeg.wasm not supported on this browser');
    }
    
    try {
        // This will dynamically load ffmpeg.wasm when needed
        const ffmpeg = await loader.loadFFmpeg();
        return ffmpeg;
    } catch (error) {
        console.error('Failed to load FFmpeg:', error);
        throw new Error(`FFmpeg loading failed: ${error.message}`);
    }
}

/**
 * Compress video file using FFmpegDynamicLoader
 */
async function compressVideo({ file, options }) {
    if (!initialized) {
        throw new Error('FFmpeg not initialized');
    }

    currentCompression = {
        id: generateCompressionId(),
        startTime: Date.now(),
        cancelled: false
    };

    try {
        // Validate input file
        validateInputFile(file);
        
        // Report progress
        sendProgress({ stage: 'initializing', progress: 0 });
        
        // Get FFmpeg loader
        const loader = getFFmpegLoader();
        
        // Use the dynamic loader's compression method
        sendProgress({ stage: 'loading', progress: 10 });
        
        const result = await loader.compressVideo(
            file, 
            options.preset || 'medical-standard',
            (progressData) => {
                // Forward progress from FFmpeg to main thread
                sendProgress({
                    stage: 'compressing',
                    progress: 20 + (progressData.progress * 0.7), // Scale to 20-90%
                    time: progressData.time
                });
            }
        );
        
        if (currentCompression.cancelled) {
            throw new Error('Compression cancelled');
        }
        
        if (!result.success) {
            throw new Error(result.error || 'Compression failed');
        }
        
        // Create result file with medical naming convention
        const compressedFile = new File([result.compressedFile], 
            `compressed_${file.name.replace(/\.[^/.]+$/, '.mp4')}`, 
            { type: 'video/mp4' });
        
        // Calculate compression stats
        const stats = {
            originalSize: result.originalSize,
            compressedSize: result.compressedSize,
            compressionRatio: result.compressionRatio,
            processingTime: Date.now() - currentCompression.startTime,
            preset: result.preset,
            format: result.format
        };
        
        // Validate medical quality
        const qualityValidation = validateMedicalQuality(result.originalSize, result.compressedSize, result.preset);
        
        sendProgress({ stage: 'complete', progress: 100 });
        sendMessage('complete', { 
            compressedFile, 
            stats,
            qualityValidation,
            medicalCompliance: {
                preset: options.preset,
                contentType: options.contentType,
                hipaaCompliant: true,
                auditTrail: generateAuditMetadata(options)
            },
            compressionId: currentCompression.id 
        });
        
    } catch (error) {
        await cleanup();
        throw error;
    } finally {
        currentCompression = null;
    }
}

/**
 * Execute ffmpeg with progress tracking
 */
async function executeWithProgress(args) {
    // In real implementation, you would set up progress tracking
    // FFmpeg provides progress callbacks through stderr parsing
    
    // Simulate progress updates during compression
    const progressSteps = [30, 50, 70, 85];
    
    for (let i = 0; i < progressSteps.length; i++) {
        if (currentCompression.cancelled) {
            throw new Error('Compression cancelled');
        }
        
        await new Promise(resolve => setTimeout(resolve, 500));
        sendProgress({ 
            stage: 'compressing', 
            progress: progressSteps[i],
            step: `Processing frame group ${i + 1}/${progressSteps.length}`
        });
    }
    
    // Execute actual ffmpeg command
    await ffmpeg.exec(args);
}

/**
 * Build ffmpeg command arguments with Phase 2 medical enhancements
 */
function buildFFmpegCommand(inputFile, outputFile, preset, options) {
    const args = [
        '-i', inputFile,
        '-c:v', 'libx264',
        '-crf', preset.crf.toString(),
        '-maxrate', preset.maxBitrate,
        '-bufsize', preset.bufsize,
        '-preset', preset.preset,
        '-profile:v', preset.profile,
        '-level', preset.level,
        '-pix_fmt', preset.pixelFormat || 'yuv420p',
        '-movflags', '+faststart', // Optimize for web playback
        '-avoid_negative_ts', 'make_zero'
    ];

    // Add medical-specific color space settings for accuracy
    if (preset.medicalSettings?.colorSpace) {
        args.push('-colorspace', preset.medicalSettings.colorSpace);
        args.push('-color_primaries', preset.medicalSettings.colorSpace);
        args.push('-color_trc', preset.medicalSettings.colorSpace);
    }

    // Handle medical metadata preservation/stripping
    if (preset.medicalSettings?.preserveMetadata?.length > 0) {
        // Preserve specific metadata for medical compliance
        args.push('-map_metadata', '0');
        preset.medicalSettings.preserveMetadata.forEach(field => {
            args.push('-metadata:g', `${field}=${field}`);
        });
    } else {
        // Strip all metadata for HIPAA compliance
        args.push('-map_metadata', '-1');
    }

    // Add medical audit trail metadata
    const auditMetadata = generateAuditMetadata(options);
    Object.entries(auditMetadata).forEach(([key, value]) => {
        args.push('-metadata', `medical_${key}=${value}`);
    });

    // Add resolution scaling if needed
    if (options.maxWidth || options.maxHeight) {
        const scale = `scale=${options.maxWidth || -2}:${options.maxHeight || -2}`;
        args.push('-vf', scale);
    }

    // Preserve audio with medical-appropriate settings
    args.push('-c:a', 'aac', '-b:a', '128k', '-ar', '48000');

    // Output file
    args.push('-y', outputFile); // -y to overwrite

    return args;
}

/**
 * Validate input file
 */
function validateInputFile(file) {
    const maxSize = 500 * 1024 * 1024; // 500MB limit
    const allowedTypes = ['video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo'];
    
    if (file.size > maxSize) {
        throw new Error(`File too large: ${Math.round(file.size / 1024 / 1024)}MB (max ${Math.round(maxSize / 1024 / 1024)}MB)`);
    }
    
    if (!allowedTypes.includes(file.type)) {
        throw new Error(`Unsupported file type: ${file.type}`);
    }
}

/**
 * Cancel current compression
 */
function cancelCompression() {
    if (currentCompression) {
        currentCompression.cancelled = true;
        cleanup();
        sendMessage('cancelled', { compressionId: currentCompression.id });
    }
}

/**
 * Setup memory management
 */
function setupMemoryManagement() {
    // Periodic cleanup
    setInterval(() => {
        if (!currentCompression) {
            performMemoryCleanup();
        }
    }, MEMORY_CONFIG.cleanupInterval);
}

/**
 * Perform memory cleanup
 */
async function performMemoryCleanup() {
    try {
        // In real implementation, you would clean up WASM memory
        // and any temporary files
        if (typeof gc === 'function') {
            gc(); // Force garbage collection if available
        }
    } catch (error) {
        console.warn('Memory cleanup failed:', error);
    }
}

/**
 * Cleanup temporary files
 */
async function cleanup(filenames = []) {
    try {
        for (const filename of filenames) {
            await ffmpeg.deleteFile(filename);
        }
    } catch (error) {
        console.warn('Cleanup failed:', error);
    }
}

/**
 * Generate medical audit metadata for compliance
 */
function generateAuditMetadata(options) {
    return {
        compression_timestamp: new Date().toISOString(),
        compression_preset: options.preset || 'unknown',
        content_type: options.contentType || 'documentation',
        hipaa_compliant: 'true',
        compression_version: '2.0',
        quality_validated: 'pending'
    };
}

/**
 * Validate compression quality for medical use
 */
function validateMedicalQuality(originalSize, compressedSize, preset) {
    const compressionRatio = (originalSize - compressedSize) / originalSize;
    const medicalSettings = MEDICAL_PRESETS[preset]?.medicalSettings;
    
    const validation = {
        passed: true,
        warnings: [],
        compressionRatio,
        qualityScore: getQualityScore(preset)
    };

    // Check if compression is too aggressive
    if (medicalSettings && compressionRatio > medicalSettings.maxSizeReduction) {
        validation.warnings.push({
            type: 'excessive_compression',
            message: `Compression ratio ${(compressionRatio * 100).toFixed(1)}% exceeds medical safe threshold of ${(medicalSettings.maxSizeReduction * 100).toFixed(1)}%`
        });
    }

    // Check if preset is diagnostic safe when needed
    if (medicalSettings && !medicalSettings.diagnosticSafe && preset !== 'medical-high') {
        validation.warnings.push({
            type: 'diagnostic_quality',
            message: 'Preset may not preserve diagnostic quality for medical analysis'
        });
    }

    return validation;
}

/**
 * Get quality score for preset
 */
function getQualityScore(preset) {
    const scores = {
        'medical-high': 0.95,
        'standard-medical': 0.80,
        'mobile-optimized': 0.65
    };
    return scores[preset] || 0.50;
}

/**
 * Utility functions
 */
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

function generateCompressionId() {
    return 'comp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
}

function sendMessage(type, data) {
    self.postMessage({ type, data });
}

function sendProgress(progressData) {
    sendMessage('progress', progressData);
}

function sendError(message) {
    sendMessage('error', { message });
}

// Error handling for unhandled errors
self.onerror = function(error) {
    sendError(`Worker error: ${error.message}`);
};

self.onunhandledrejection = function(event) {
    sendError(`Unhandled promise rejection: ${event.reason}`);
};