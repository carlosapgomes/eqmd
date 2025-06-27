/**
 * VideoClip Player - JavaScript for EquipeMed MediaFiles
 * 
 * Handles video player controls and modal interactions
 */

// VideoClip namespace
window.VideoClipPlayer = (function() {
    'use strict';

    // Video player controls
    const videoPlayer = {
        /**
         * Initialize video player functionality
         */
        init: function() {
            this.setupVideoPlayers();
            this.setupModalControls();
        },

        /**
         * Setup video players
         */
        setupVideoPlayers: function() {
            const videos = document.querySelectorAll('video');

            videos.forEach(video => {
                this.enhanceVideoPlayer(video);
            });
        },

        /**
         * Enhance individual video player
         */
        enhanceVideoPlayer: function(video) {
            // Add loading indicator
            video.addEventListener('loadstart', function() {
                this.style.cursor = 'wait';
            });

            video.addEventListener('canplay', function() {
                this.style.cursor = 'default';
            });

            // Error handling
            video.addEventListener('error', function() {
                console.error('Video loading error:', this.error);
                const errorMsg = document.createElement('div');
                errorMsg.className = 'alert alert-danger text-center';
                errorMsg.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>Erro ao carregar o vídeo. Tente novamente ou baixe o arquivo.';
                this.parentNode.replaceChild(errorMsg, this);
            });

            // Keyboard controls
            video.addEventListener('keydown', function(e) {
                switch(e.key) {
                    case ' ':
                        e.preventDefault();
                        if (this.paused) {
                            this.play();
                        } else {
                            this.pause();
                        }
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        this.currentTime = Math.max(0, this.currentTime - 10);
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        this.currentTime = Math.min(this.duration, this.currentTime + 10);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        this.volume = Math.min(1, this.volume + 0.1);
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        this.volume = Math.max(0, this.volume - 0.1);
                        break;
                    case 'm':
                    case 'M':
                        e.preventDefault();
                        this.muted = !this.muted;
                        break;
                }
            });

            // Add focus capability for keyboard navigation
            video.setAttribute('tabindex', '0');
        },

        /**
         * Setup modal controls
         */
        setupModalControls: function() {
            const videoModal = document.getElementById('videoModal');
            const modalVideo = document.getElementById('modalVideo');

            if (videoModal && modalVideo) {
                videoModal.addEventListener('shown.bs.modal', function() {
                    modalVideo.focus();
                });

                videoModal.addEventListener('hidden.bs.modal', function() {
                    modalVideo.pause();
                    modalVideo.currentTime = 0;
                });
            }
        }
    };

    // Public API
    return {
        /**
         * Initialize video player functionality
         */
        init: function() {
            videoPlayer.init();
        }
    };
})();