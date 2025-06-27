/**
 * FFmpeg Dynamic Loader - Lazy loads ffmpeg.wasm only when needed
 * Replaces the mock implementation with real video compression
 */
class FFmpegDynamicLoader {
    constructor() {
        this.ffmpegInstance = null;
        this.isLoaded = false;
        this.isLoading = false;
        this.loadPromise = null;
    }

    /**
     * Dynamically load ffmpeg.wasm when compression is needed
     */
    async loadFFmpeg() {
        if (this.isLoaded && this.ffmpegInstance) {
            return this.ffmpegInstance;
        }

        if (this.isLoading) {
            return this.loadPromise;
        }

        this.isLoading = true;
        
        try {
            this.loadPromise = this._loadFFmpegModules();
            this.ffmpegInstance = await this.loadPromise;
            this.isLoaded = true;
            return this.ffmpegInstance;
        } catch (error) {
            this.isLoading = false;
            this.loadPromise = null;
            throw new Error(`Failed to load FFmpeg: ${error.message}`);
        }
    }

    /**
     * Internal method to load ffmpeg modules dynamically
     */
    async _loadFFmpegModules() {
        // Dynamic import - webpack will create separate chunk
        const { FFmpeg } = await import('@ffmpeg/ffmpeg');
        const { toBlobURL } = await import('@ffmpeg/util');

        const ffmpeg = new FFmpeg();

        // Configure logging for debugging
        ffmpeg.on('log', ({ message }) => {
            console.log('[FFmpeg]', message);
        });

        ffmpeg.on('progress', ({ progress, time }) => {
            // This will be used by the compression worker
            self.postMessage({
                type: 'progress',
                progress: progress * 100,
                time: time
            });
        });

        // Load FFmpeg core - use CDN for WASM files as they can't be bundled
        const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm';
        
        await ffmpeg.load({
            coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
            wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
            workerURL: await toBlobURL(`${baseURL}/ffmpeg-core.worker.js`, 'text/javascript'),
        });

        console.log('FFmpeg loaded successfully');
        return ffmpeg;
    }

    /**
     * Check if ffmpeg is available without loading it
     */
    isFFmpegAvailable() {
        // Check for WebAssembly support
        if (typeof WebAssembly === 'undefined') {
            return false;
        }

        // Check for SharedArrayBuffer support (required by ffmpeg.wasm)
        if (typeof SharedArrayBuffer === 'undefined') {
            console.warn('SharedArrayBuffer not available - ffmpeg.wasm may not work');
            // Don't return false as some versions work without SharedArrayBuffer
        }

        return true;
    }

    /**
     * Get compression presets optimized for medical content
     */
    getMedicalPresets() {
        return {
            'medical-high': {
                quality: 'high',
                crf: 18,
                preset: 'medium',
                profile: 'high',
                maxBitrate: '8M',
                description: 'High quality for diagnostic content'
            },
            'medical-standard': {
                quality: 'standard', 
                crf: 23,
                preset: 'medium',
                profile: 'main',
                maxBitrate: '4M',
                description: 'Balanced quality and file size'
            },
            'mobile-optimized': {
                quality: 'optimized',
                crf: 28,
                preset: 'fast',
                profile: 'baseline',
                maxBitrate: '2M',
                description: 'Fast compression for mobile devices'
            }
        };
    }

    /**
     * Build ffmpeg command arguments for compression
     */
    buildCompressionArgs(inputFile, outputFile, preset = 'medical-standard') {
        const presets = this.getMedicalPresets();
        const config = presets[preset] || presets['medical-standard'];

        return [
            '-i', inputFile,
            '-c:v', 'libx264',
            '-crf', config.crf.toString(),
            '-preset', config.preset,
            '-profile:v', config.profile,
            '-maxrate', config.maxBitrate,
            '-bufsize', (parseInt(config.maxBitrate) * 2) + 'M',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-pix_fmt', 'yuv420p',
            '-colorspace', 'bt709', // Medical standard color space
            outputFile
        ];
    }

    /**
     * Compress video file using the loaded ffmpeg instance
     */
    async compressVideo(videoFile, preset = 'medical-standard', onProgress = null) {
        if (!this.isFFmpegAvailable()) {
            throw new Error('FFmpeg not available on this browser');
        }

        const ffmpeg = await this.loadFFmpeg();
        
        try {
            // Convert file to Uint8Array
            const videoData = new Uint8Array(await videoFile.arrayBuffer());
            
            // Input and output filenames
            const inputName = 'input.' + this._getFileExtension(videoFile.name);
            const outputName = 'output.mp4';

            // Write input file to FFmpeg filesystem
            await ffmpeg.writeFile(inputName, videoData);

            // Build compression arguments
            const args = this.buildCompressionArgs(inputName, outputName, preset);

            // Execute compression
            await ffmpeg.exec(args);

            // Read compressed file
            const compressedData = await ffmpeg.readFile(outputName);
            
            // Create blob from compressed data
            const compressedBlob = new Blob([compressedData], { type: 'video/mp4' });
            
            // Clean up FFmpeg filesystem
            await this._cleanup(ffmpeg, [inputName, outputName]);

            return {
                success: true,
                compressedFile: compressedBlob,
                compressionRatio: compressedBlob.size / videoFile.size,
                originalSize: videoFile.size,
                compressedSize: compressedBlob.size,
                format: 'mp4',
                preset: preset
            };

        } catch (error) {
            console.error('Compression failed:', error);
            return {
                success: false,
                error: error.message,
                originalFile: videoFile
            };
        }
    }

    /**
     * Get file extension from filename
     */
    _getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    /**
     * Clean up FFmpeg filesystem
     */
    async _cleanup(ffmpeg, filenames) {
        for (const filename of filenames) {
            try {
                await ffmpeg.deleteFile(filename);
            } catch (error) {
                console.warn(`Failed to delete ${filename}:`, error);
            }
        }
    }

    /**
     * Terminate FFmpeg instance to free memory
     */
    terminate() {
        if (this.ffmpegInstance) {
            this.ffmpegInstance.terminate();
            this.ffmpegInstance = null;
            this.isLoaded = false;
        }
    }
}

// Export for use in workers and main thread
if (typeof window !== 'undefined') {
    window.FFmpegDynamicLoader = FFmpegDynamicLoader;
} else {
    // In worker context
    self.FFmpegDynamicLoader = FFmpegDynamicLoader;
}