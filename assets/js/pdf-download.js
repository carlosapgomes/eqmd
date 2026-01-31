/**
 * PDF Download functionality with spinner
 * 
 * Features:
 * - Fetch-based download (no page reload)
 * - Loading spinner during generation
 * - Automatic file download
 * - Error handling with user feedback
 * - Proper cleanup of object URLs
 * - Opens PDF in a new tab (no forced download)
 */

class PDFDownloader {
  constructor() {
    this.initialize();
  }

  initialize() {
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Use event delegation for dynamically added buttons
    document.addEventListener('click', (e) => {
      if (e.target.closest('.pdf-download-btn')) {
        e.preventDefault();
        this.handlePdfDownload(e.target.closest('.pdf-download-btn'));
      }
    });
  }

  async handlePdfDownload(button) {
    const pdfUrl = button.dataset.pdfUrl;
    const filename = button.dataset.filename || 'document.pdf';
    const contentSpan = button.querySelector('.pdf-btn-content');
    const spinnerSpan = button.querySelector('.pdf-btn-spinner');
    const newTab = this.openPlaceholderTab();
    
    if (!pdfUrl) {
      console.error('PDF URL not found');
      if (newTab) {
        newTab.close();
      }
      return;
    }
    
    try {
      // Show loading state
      this.setLoadingState(button, contentSpan, spinnerSpan, true);
      
      // Fetch PDF with timeout
      const response = await this.fetchWithTimeout(pdfUrl, 30000); // 30 second timeout
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Verify content type
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/pdf')) {
        throw new Error('Response is not a PDF file');
      }
      
      // Get PDF blob
      const blob = await response.blob();
      
      if (blob.size === 0) {
        throw new Error('PDF file is empty');
      }
      
      // Create object URL
      const pdfObjectUrl = URL.createObjectURL(blob);

      // Open in new tab (for printing/viewing)
      this.openInNewTab(newTab, pdfObjectUrl, filename);

      // Clean up object URL after delay
      this.scheduleCleanup(pdfObjectUrl);

      // Show success feedback
      this.showSuccessMessage('PDF gerado com sucesso!');
      
    } catch (error) {
      console.error('Error downloading PDF:', error);
      this.showErrorMessage(this.getErrorMessage(error));
      if (newTab) {
        newTab.close();
      }
    } finally {
      // Hide loading state
      this.setLoadingState(button, contentSpan, spinnerSpan, false);
    }
  }

  async fetchWithTimeout(url, timeout = 30000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  setLoadingState(button, contentSpan, spinnerSpan, isLoading) {
    if (isLoading) {
      contentSpan?.classList.add('d-none');
      spinnerSpan?.classList.remove('d-none');
      button.disabled = true;
      button.style.cursor = 'wait';
    } else {
      contentSpan?.classList.remove('d-none');
      spinnerSpan?.classList.add('d-none');
      button.disabled = false;
      button.style.cursor = '';
    }
  }

  openPlaceholderTab() {
    try {
      return window.open('', '_blank');
    } catch (error) {
      return null;
    }
  }

  openInNewTab(newTab, objectUrl, filename) {
    if (newTab) {
      newTab.document.title = filename;
      newTab.location = objectUrl;
      newTab.focus();
      return;
    }

    // Fallback if popup was blocked
    window.open(objectUrl, '_blank');
  }

  scheduleCleanup(objectUrl) {
    // Clean up object URL after 2 seconds to allow browser to process
    setTimeout(() => {
      URL.revokeObjectURL(objectUrl);
    }, 2000);
  }

  getErrorMessage(error) {
    if (error.name === 'AbortError') {
      return 'Tempo esgotado. Tente novamente.';
    } else if (error.message.includes('HTTP error! status: 404')) {
      return 'PDF não encontrado.';
    } else if (error.message.includes('HTTP error! status: 500')) {
      return 'Erro interno do servidor. Tente novamente.';
    } else if (error.message.includes('not a PDF file')) {
      return 'Arquivo recebido não é um PDF válido.';
    } else if (error.message.includes('empty')) {
      return 'PDF gerado está vazio.';
    } else {
      return 'Erro ao gerar PDF. Tente novamente.';
    }
  }

  showSuccessMessage(message) {
    this.showMessage(message, 'success', 'check-circle');
  }

  showErrorMessage(message) {
    this.showMessage(message, 'danger', 'exclamation-triangle');
  }

  showMessage(message, type, iconClass) {
    // Remove existing messages
    const existing = document.querySelectorAll('.pdf-download-message');
    existing.forEach(msg => msg.remove());

    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed pdf-download-message`;
    messageDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 400px;';
    messageDiv.innerHTML = `
      <i class="bi bi-${iconClass} me-2"></i>
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(messageDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      if (messageDiv.parentNode) {
        messageDiv.classList.remove('show');
        setTimeout(() => {
          if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
          }
        }, 150);
      }
    }, 5000);
  }
}

// Initialize PDF downloader when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  new PDFDownloader();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PDFDownloader;
}
