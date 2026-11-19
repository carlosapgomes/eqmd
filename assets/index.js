// Import custom Bootstrap theme
import './scss/main.scss';

import { copyTextToClipboard, showClipboardFeedback } from './js/clipboard-utils.js';
import { initDailyNoteCopy } from './js/dailynote-copy.js';

// Clipboard functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeClipboardButtons();
    initDailyNoteCopy();
});

function initializeClipboardButtons() {
    // Handle copy to clipboard functionality
    document.addEventListener('click', function(e) {
        const copyBtn = e.target.closest('.copy-content-btn');
        if (copyBtn) {
            e.preventDefault();
            copyToClipboard(copyBtn);
        }
    });
}

async function copyToClipboard(button) {
    const content = button.dataset.content;
    
    if (!content) {
        showClipboardFeedback(button, false, 'Nenhum conteúdo para copiar');
        return;
    }
    
    try {
        await copyTextToClipboard(content);
        showClipboardFeedback(button, true);
    } catch (error) {
        console.error('Failed to copy text:', error);
        showClipboardFeedback(button, false, 'Falha ao copiar conteúdo');
    }
}

// Debug code removed for production
