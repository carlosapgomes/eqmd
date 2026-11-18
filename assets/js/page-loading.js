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
    
    let pendingLoading;
    let loadingTimeout;

    // Show loading overlay
    function showLoading() {
        loadingOverlay.classList.remove('d-none');
    }
    
    // Hide loading overlay
    function hideLoading() {
        clearTimeout(pendingLoading);
        clearTimeout(loadingTimeout);
        loadingOverlay.classList.add('d-none');
    }

    // Cancellation can happen in a later listener during the same dispatch.
    function scheduleLoading(event, delay) {
        if (event.defaultPrevented) {
            return;
        }
        clearTimeout(pendingLoading);
        pendingLoading = setTimeout(function() {
            if (event.defaultPrevented) {
                return;
            }
            showLoading();
            clearTimeout(loadingTimeout);
            loadingTimeout = setTimeout(hideLoading, 15000);
        }, delay);
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
    
    // Check if form should trigger loading indicator
    function shouldShowFormLoading(form) {
        // Skip forms that explicitly opt out
        if (form.hasAttribute('data-no-loading') || form.classList.contains('no-loading')) {
            return false;
        }
        
        // Skip AJAX forms
        if (form.hasAttribute('data-ajax') || form.classList.contains('ajax-form')) {
            return false;
        }
        
        // Skip forms that stay on same page (method=GET with no action change)
        const method = form.method?.toLowerCase() || 'get';
        const action = form.action;
        
        // Skip GET forms that don't change URL (like search/filter forms)
        if (method === 'get' && (!action || action === window.location.href || action === window.location.pathname)) {
            return false;
        }
        
        return true;
    }
    
    // Add click event listeners to navigation links and form submissions
    function initializeNavLoading() {
        document.addEventListener('click', function(event) {
            if (event.button > 0 || event.ctrlKey || event.metaKey ||
                event.shiftKey || event.altKey) {
                return;
            }
            const link = event.target.closest('a');
            if (link && shouldShowLoading(link)) {
                // Keep the existing delay without masking intercepted clicks.
                scheduleLoading(event, 100);
            }
        });

        document.addEventListener('submit', function(event) {
            if (shouldShowFormLoading(event.target)) {
                // Wait for all submit listeners before treating this as navigation.
                scheduleLoading(event, 0);
            }
        });

        window.addEventListener('pageshow', hideLoading);
        window.addEventListener('load', hideLoading);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeNavLoading);
    } else {
        initializeNavLoading();
    }
})();