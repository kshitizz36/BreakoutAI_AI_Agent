// Main JavaScript file for enhanced functionality

// File Upload Preview
function handleFileUpload(input) {
    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                // For CSV files
                const csvData = e.target.result;
                displayPreview(csvData);
            } catch (error) {
                console.error('Error processing file:', error);
                showError('Error processing file. Please check the format.');
            }
        };
        reader.readAsText(file);
    }
}

// Display Preview of Data
function displayPreview(data) {
    const previewContainer = document.getElementById('data-preview');
    if (previewContainer) {
        const rows = data.split('\n').slice(0, 5); // Show first 5 rows
        const table = document.createElement('table');
        table.className = 'preview-table';
        
        rows.forEach((row, index) => {
            const tr = document.createElement('tr');
            const cells = row.split(',');
            
            cells.forEach(cell => {
                const el = index === 0 ? 'th' : 'td';
                const cellElement = document.createElement(el);
                cellElement.textContent = cell;
                tr.appendChild(cellElement);
            });
            
            table.appendChild(tr);
        });
        
        previewContainer.innerHTML = '';
        previewContainer.appendChild(table);
    }
}

// Enhanced Error Handling
function showError(message) {
    const errorContainer = document.createElement('div');
    errorContainer.className = 'error-message';
    errorContainer.textContent = message;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorContainer.remove();
    }, 5000);
    
    document.body.appendChild(errorContainer);
}

// Progress Indicator
class ProgressIndicator {
    constructor() {
        this.progress = 0;
        this.element = document.createElement('div');
        this.element.className = 'progress-bar';
        document.body.appendChild(this.element);
    }
    
    update(value) {
        this.progress = value;
        this.element.style.width = `${value}%`;
    }
    
    complete() {
        this.update(100);
        setTimeout(() => {
            this.element.remove();
        }, 1000);
    }
}

// Dynamic Form Validation
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value) {
            isValid = false;
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }
    });
    
    return isValid;
}

// Download Handler
function handleDownload(data, filename) {
    const blob = new Blob([data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => handleFileUpload(e.target));
    }
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseover', function() {
            this.querySelector('.tooltiptext').style.visibility = 'visible';
        });
        tooltip.addEventListener('mouseout', function() {
            this.querySelector('.tooltiptext').style.visibility = 'hidden';
        });
    });
});

// Export functions for Streamlit
window.handleFileUpload = handleFileUpload;
window.showError = showError;
window.handleDownload = handleDownload;