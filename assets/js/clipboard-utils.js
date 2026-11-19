// Shared clipboard helpers for card copy flows (design D3).

export async function copyTextToClipboard(text) {
    // Try modern Clipboard API first
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }

    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    textArea.style.pointerEvents = 'none';
    document.body.appendChild(textArea);
    textArea.select();

    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);

    if (!successful) {
        throw new Error('Copy command failed');
    }
}

export function showClipboardFeedback(button, success, message = null) {
    const icon = button.querySelector('i');
    const originalClass = icon.className;
    
    if (success) {
        // Change icon to checkmark
        icon.className = 'bi bi-check me-1';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-success');
        
        // Show toast notification
        showToast('Conteúdo copiado para a área de transferência!', 'success');
    } else {
        // Change icon to X
        icon.className = 'bi bi-x me-1';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-danger');
        
        // Show error toast
        showToast(message || 'Erro ao copiar conteúdo', 'danger');
    }
    
    // Revert after 2 seconds
    setTimeout(() => {
        icon.className = originalClass;
        button.classList.remove('btn-success', 'btn-danger');
        button.classList.add('btn-outline-secondary');
    }, 2000);
}

export function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.ariaAtomic = 'true';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Initialize and show toast - check if Bootstrap is available
    if (typeof window.bootstrap !== 'undefined' && window.bootstrap.Toast) {
        const bsToast = new window.bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    } else {
        // Fallback: auto-remove toast after delay if Bootstrap is not available
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    }
}
