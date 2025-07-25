document.addEventListener('DOMContentLoaded', function() {
    
    // Form validation enhancement
    const pdfForms = document.querySelectorAll('.pdf-form');
    pdfForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                // Show first invalid field
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });

    // Date field enhancement
    const dateFields = document.querySelectorAll('input[type="date"]');
    dateFields.forEach(field => {
        // Ensure proper date format for browsers that don't support date input
        if (field.type !== 'date') {
            field.placeholder = 'DD/MM/AAAA';
            field.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length >= 2) {
                    value = value.substring(0, 2) + '/' + value.substring(2);
                }
                if (value.length >= 5) {
                    value = value.substring(0, 5) + '/' + value.substring(5, 9);
                }
                e.target.value = value;
            });
        }
    });

    // Number field validation
    const numberFields = document.querySelectorAll('input[type="number"]');
    numberFields.forEach(field => {
        field.addEventListener('input', function(e) {
            const value = e.target.value;
            if (value && isNaN(value)) {
                e.target.classList.add('is-invalid');
            } else {
                e.target.classList.remove('is-invalid');
            }
        });
    });

    // Textarea auto-resize
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });

    // Form field help tooltips
    const helpTexts = document.querySelectorAll('.form-text');
    helpTexts.forEach(help => {
        help.addEventListener('click', function() {
            this.style.display = this.style.display === 'none' ? 'block' : 'none';
        });
    });

    // Confirmation dialog for form submission
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Confirma o envio do formulário?')) {
                e.preventDefault();
            }
        });
    });

    // Download button enhancement
    const downloadLinks = document.querySelectorAll('a[href*="download"]');
    downloadLinks.forEach(link => {
        link.addEventListener('click', function() {
            this.classList.add('disabled');
            this.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Preparando...';
            
            setTimeout(() => {
                this.classList.remove('disabled');
                this.innerHTML = '<i class="bi bi-download me-1"></i> Baixar PDF';
            }, 2000);
        });
    });

    // Print functionality
    const printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(button => {
        button.addEventListener('click', function() {
            window.print();
        });
    });

    // Form data preview (for debugging)
    if (window.location.search.includes('debug=1')) {
        console.log('PDF Forms Debug Mode Active');
        
        const forms = document.querySelectorAll('.pdf-form');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(form);
                const data = Object.fromEntries(formData);
                console.log('Form Data:', data);
                
                // Show data in alert for debugging
                alert('Dados do formulário:\n' + JSON.stringify(data, null, 2));
            });
        });
    }
});