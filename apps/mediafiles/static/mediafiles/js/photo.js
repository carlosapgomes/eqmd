/**
 * Photo-specific JavaScript for EquipeMed MediaFiles
 * 
 * Handles photo upload, preview, validation, and modal interactions.
 * Implements modern client-side image compression and HEIC conversion.
 */

import imageCompression from 'browser-image-compression';
import heic2any from 'heic2any';

// Photo namespace
window.Photo = (function() {
    'use strict';

    // --- Configuration ---
    const compressionOptions = {
        maxSizeMB: 2,
        maxWidthOrHeight: 1920,
        useWebWorker: true,
        initialQuality: 0.8,
        mimeType: 'image/jpeg',
    };

    // --- Shared Utilities ---
    const utils = window.MediaFiles ? window.MediaFiles.utils : {
        formatFileSize: (bytes) => {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },
        showToast: (message, type = 'info') => {
            console.log(`Toast (${type}): ${message}`);
        }
    };

    // --- Core Photo Upload Logic ---
    const photoUpload = {
        init: function() {
            this.cacheDOMElements();
            this.setupEventListeners();
        },

        cacheDOMElements: function() {
            this.uploadArea = document.getElementById('uploadArea');
            this.fileInput = document.querySelector('input[type="file"][name="image"]');
            this.imagePreview = document.getElementById('imagePreview');
            this.previewImage = document.getElementById('previewImage');
            this.removeImageBtn = document.getElementById('removeImage');
            this.uploadProgress = document.getElementById('uploadProgress');
            this.progressBar = document.getElementById('progressBar');
            this.fileNameEl = document.getElementById('fileName');
            this.fileSizeEl = document.getElementById('fileSize');
            this.fileTypeEl = document.getElementById('fileType');
        },

        setupEventListeners: function() {
            if (this.uploadArea) {
                this.uploadArea.addEventListener('click', () => this.fileInput.click());
                this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
                this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
                this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
            }
            if (this.fileInput) {
                this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
            }
            if (this.removeImageBtn) {
                this.removeImageBtn.addEventListener('click', this.removePreview.bind(this));
            }
        },

        handleDragOver: function(e) {
            e.preventDefault();
            this.uploadArea.classList.add('dragover');
        },

        handleDragLeave: function(e) {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
        },

        handleDrop: function(e) {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.fileInput.files = files;
                this.handleFileSelect({ target: this.fileInput });
            }
        },

        handleFileSelect: async function(e) {
            const originalFile = e.target.files[0];
            if (!originalFile) return;

            this.showUploadProgress('Processando imagem...');

            try {
                const convertedFile = await this.convertHeicToJpeg(originalFile);
                const compressedBlob = await imageCompression(convertedFile, compressionOptions);
                
                const finalFile = new File([compressedBlob], convertedFile.name.replace(/\.[^/.]+$/, ".jpg"), {
                    type: 'image/jpeg',
                    lastModified: Date.now()
                });

                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(finalFile);
                this.fileInput.files = dataTransfer.files;

                this.displayPreview(finalFile);
                if(utils.showToast) {
                    utils.showToast('Imagem pronta para envio!', 'success');
                }

            } catch (error) {
                console.error('Image processing error:', error);
                if(utils.showToast) {
                    utils.showToast(`Erro ao processar imagem: ${error.message}`, 'danger');
                }
                this.reset();
            } finally {
                this.hideUploadProgress();
            }
        },

        convertHeicToJpeg: async function(file) {
            const fileName = file.name.toLowerCase();
            const isHeic = fileName.endsWith('.heic') || fileName.endsWith('.heif') || file.type === 'image/heic' || file.type === 'image/heif';
            
            if (isHeic) {
                this.showUploadProgress('Convertendo imagem HEIC...');
                try {
                    const conversionResult = await heic2any({
                        blob: file,
                        toType: 'image/jpeg',
                        quality: 0.9,
                    });
                    const newFileName = file.name.replace(/\.(heic|heif)$/i, '.jpg');
                    return new File([conversionResult], newFileName, { type: 'image/jpeg' });
                } catch (err) {
                    console.error("HEIC conversion failed:", err);
                    throw new Error("Falha ao converter imagem HEIC.");
                }
            }
            return file;
        },

        displayPreview: function(file) {
            const imageURL = URL.createObjectURL(file);
            if(this.previewImage) {
                this.previewImage.src = imageURL;
                this.previewImage.onload = () => URL.revokeObjectURL(this.previewImage.src);
            }

            if (this.fileNameEl) this.fileNameEl.textContent = file.name;
            if (this.fileSizeEl) this.fileSizeEl.textContent = utils.formatFileSize(file.size);
            if (this.fileTypeEl) this.fileTypeEl.textContent = file.type;

            if (this.imagePreview) this.imagePreview.style.display = 'block';
            if (this.uploadArea) this.uploadArea.style.display = 'none';
        },

        removePreview: function() {
            this.reset();
        },
        
        reset: function() {
            if(this.fileInput) {
                this.fileInput.value = '';
            }
            if (this.imagePreview) this.imagePreview.style.display = 'none';
            if (this.uploadArea) this.uploadArea.style.display = 'block';
            if(this.previewImage) {
                this.previewImage.src = '';
            }
            this.hideUploadProgress();
        },

        showUploadProgress: function(message = 'Processando...') {
            if (this.uploadProgress && this.progressBar) {
                this.uploadProgress.style.display = 'block';
                this.progressBar.style.width = '50%';
                this.progressBar.textContent = message;
            }
        },

        hideUploadProgress: function() {
            if (this.uploadProgress && this.progressBar) {
                this.uploadProgress.style.display = 'none';
                this.progressBar.style.width = '0%';
                this.progressBar.textContent = '';
            }
        }
    };

    // --- Public API ---
    return {
        init: function() {
            if (document.getElementById('photoForm')) {
                photoUpload.init();
            }
        }
    };
})();
