/**
 * VideoClip JavaScript - Simple FilePond-based video upload
 * 
 * This module provides basic video upload functionality using FilePond
 * with server-side H.264 conversion.
 */

// Simple initialization for video upload forms
document.addEventListener('DOMContentLoaded', function() {
    console.log('VideoClip module initialized');
    
    // Basic form validation
    const form = document.querySelector('form[method="post"]');
    if (form) {
        form.addEventListener('submit', function(e) {
            const uploadId = document.querySelector('input[name="upload_id"]');
            if (uploadId && !uploadId.value) {
                e.preventDefault();
                alert('Por favor, faça o upload de um arquivo de vídeo primeiro.');
                return false;
            }
        });
    }
});