/**
 * Page Navigation Loading Indicator
 * Shows loading overlay during page navigation
 * Safe implementation that avoids interfering with existing functionality
 */

(function() {
    'use strict';
    
    const loadingOverlay = document.getElementById('pageLoadingOverlay');
    
    if (!loadingOverlay) {
        console.warn('Page loading overlay element not found');
        return;
    }
    
    // Show loading overlay
    function showLoading() {
        loadingOverlay.classList.remove('d-none');
    }
    
    // Hide loading overlay
    function hideLoading() {
        loadingOverlay.classList.add('d-none');
    }
    
    // Check if link should trigger loading indicator
    function shouldShowLoading(link) {
        // Skip external links
        if (link.hostname && link.hostname !== window.location.hostname) {
            return false;
        }
        
        // Skip anchors (hash links)
        if (link.getAttribute('href')?.startsWith('#')) {
            return false;
        }
        
        // Skip javascript: links
        if (link.getAttribute('href')?.startsWith('javascript:')) {
            return false;
        }
        
        // Skip mailto: and tel: links
        if (link.protocol === 'mailto:' || link.protocol === 'tel:') {
            return false;
        }
        
        // Skip links that open in new tab/window
        if (link.target === '_blank' || link.target === '_new') {
            return false;
        }
        
        // Skip data-bs-toggle links (Bootstrap modals, dropdowns, etc.)
        if (link.hasAttribute('data-bs-toggle')) {
            return false;
        }
        
        // Skip download links
        if (link.hasAttribute('download')) {
            return false;
        }
        
        // Skip specific classes that shouldn't trigger loading
        const skipClasses = [
            'no-loading',           // Manual override
            'copy-content-btn',     // Clipboard functionality
            'dropdown-toggle'       // Dropdown triggers
        ];
        
        for (const className of skipClasses) {
            if (link.classList.contains(className)) {
                return false;
            }
        }
        
        // Skip navbar dropdown nav-links (but allow sidebar nav-links)
        // Only skip nav-links that have dropdown functionality
        if (link.classList.contains('nav-link') && (
            link.hasAttribute('data-bs-toggle') || 
            link.closest('.dropdown')
        )) {
            return false;
        }
        
        return true;
    }
    
    // Add click event listeners to navigation links
    function initializeNavLoading() {
        // Listen to all link clicks
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a');
            
            if (!link || !shouldShowLoading(link)) {
                return;
            }
            
            // Show loading with small delay to avoid flicker on fast responses
            setTimeout(showLoading, 100);
        });
        
        // Hide loading when page starts to unload (navigation is happening)
        window.addEventListener('beforeunload', function() {
            // Keep loading visible during navigation
        });
        
        // Hide loading if user comes back to page (back button)
        window.addEventListener('pageshow', function(event) {
            hideLoading();
        });
        
        // Hide loading on page load
        window.addEventListener('load', function() {
            hideLoading();
        });
        
        // Safety: Hide loading after maximum time
        let loadingTimeout;
        function resetLoadingTimeout() {
            clearTimeout(loadingTimeout);
            loadingTimeout = setTimeout(hideLoading, 15000); // 15 second max
        }
        
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a');
            if (link && shouldShowLoading(link)) {
                resetLoadingTimeout();
            }
        });
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeNavLoading);
    } else {
        initializeNavLoading();
    }
})();