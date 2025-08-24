/**
 * Hamilton Transport Management - School Transportation Management System
 * Main JavaScript file for enhanced user interactions
 */

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    initializeTooltips();
    initializePopovers();
    initializeFormValidation();
    initializeTableSorting();
    initializeSearchFunctionality();
    initializeAutoRefresh();
    initializeConfirmationDialogs();
    initializeNotifications();
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap popovers
 */
function initializePopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Get all forms with validation
    const forms = document.querySelectorAll('.needs-validation');
    
    // Add validation to each form
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Real-time validation for specific fields
    const requiredFields = document.querySelectorAll('input[required], select[required], textarea[required]');
    Array.from(requiredFields).forEach(field => {
        field.addEventListener('blur', function() {
            validateField(field);
        });

        field.addEventListener('input', function() {
            if (field.classList.contains('is-invalid')) {
                validateField(field);
            }
        });
    });
}

/**
 * Validate individual field
 */
function validateField(field) {
    if (field.checkValidity()) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
    } else {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
    }
}

/**
 * Initialize table sorting functionality
 */
function initializeTableSorting() {
    // Skip sorting initialization for students page as it has custom sorting  
    if (window.location.pathname.includes('/students')) {
        return;
    }
    
    // Skip sorting initialization for Route Admin (schools page) - alphabetical by default
    if (window.location.pathname.includes('/schools')) {
        return;
    }
    
    const tables = document.querySelectorAll('table.sortable');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            // Create sort icon using safe DOM methods
            const sortIcon = document.createElement('i');
            sortIcon.className = 'fas fa-sort text-muted';
            sortIcon.style.marginLeft = '8px';
            header.appendChild(sortIcon);
            
            header.addEventListener('click', function() {
                const column = this.dataset.sort;
                const direction = this.dataset.direction || 'asc';
                const newDirection = direction === 'asc' ? 'desc' : 'asc';
                
                // Update header
                this.dataset.direction = newDirection;
                const icon = this.querySelector('i');
                icon.className = `fas fa-sort-${newDirection === 'asc' ? 'up' : 'down'}`;
                
                // Reset other headers
                headers.forEach(h => {
                    if (h !== this) {
                        h.removeAttribute('data-direction');
                        h.querySelector('i').className = 'fas fa-sort text-muted';
                    }
                });
                
                // Sort table
                sortTableGeneric(table, column, newDirection);
            });
        });
    });
}

/**
 * Sort table by column
 */
function sortTableGeneric(table, column, direction) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const columnIndex = Array.from(table.querySelectorAll('th')).findIndex(th => th.dataset.sort === column);
    
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim();
        const bValue = b.cells[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // Compare as strings
        return direction === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
    });
    
    // Reorder rows
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Initialize search functionality
 */
function initializeSearchFunctionality() {
    const searchInputs = document.querySelectorAll('.table-search');
    
    searchInputs.forEach(input => {
        const tableId = input.dataset.table;
        const table = document.getElementById(tableId);
        
        if (table) {
            input.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const rows = table.querySelectorAll('tbody tr');
                
                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        }
    });
}

/**
 * Initialize auto-refresh functionality for dashboard
 */
function initializeAutoRefresh() {
    if (window.location.pathname === '/dashboard') {
        // Auto-refresh dashboard every 5 minutes
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                refreshDashboardStats();
            }
        }, 300000); // 5 minutes
    }
}

/**
 * Refresh dashboard statistics
 */
function refreshDashboardStats() {
    fetch('/api/dashboard-stats', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        updateDashboardStats(data);
    })
    .catch(error => {
        console.error('Error refreshing dashboard stats:', error);
    });
}

/**
 * Update dashboard statistics display
 */
function updateDashboardStats(data) {
    const statsElements = {
        'total-schools': data.total_schools,
        'total-buses': data.total_buses,
        'ready-buses': data.ready_buses,
        'total-staff': data.total_staff,
        'total-students': data.total_students
    };
    
    Object.entries(statsElements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Initialize confirmation dialogs
 */
function initializeConfirmationDialogs() {
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.dataset.confirm;
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Initialize notification system
 */
function initializeNotifications() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.add('fade');
                setTimeout(() => {
                    alert.remove();
                }, 150);
            }
        }, 5000);
    });
}

/**
 * Show loading state on form submission
 */
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        // Store original text content safely
        if (!submitBtn.dataset.originalText) {
            submitBtn.dataset.originalText = submitBtn.textContent.trim() || 'Submit';
        }
        submitBtn.disabled = true;
        
        // Clear and rebuild content safely
        submitBtn.innerHTML = '';
        const spinner = document.createElement('i');
        spinner.className = 'fas fa-spinner fa-spin me-2';
        const text = document.createTextNode('Processing...');
        submitBtn.appendChild(spinner);
        submitBtn.appendChild(text);
    }
}

/**
 * Hide loading state
 */
function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = false;
        // Use textContent for safe text restoration
        submitBtn.textContent = submitBtn.dataset.originalText || 'Submit';
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.role = 'alert';
    
    // Build toast structure safely using DOM methods
    const flexDiv = document.createElement('div');
    flexDiv.className = 'd-flex';
    
    const toastBody = document.createElement('div');
    toastBody.className = 'toast-body';
    toastBody.textContent = message; // Safe text insertion
    
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close btn-close-white me-2 m-auto';
    closeButton.setAttribute('data-bs-dismiss', 'toast');
    
    flexDiv.appendChild(toastBody);
    flexDiv.appendChild(closeButton);
    toast.appendChild(flexDiv);
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Create toast container if it doesn't exist
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '11';
    document.body.appendChild(container);
    return container;
}

/**
 * Utility function to format numbers with commas
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Utility function to format dates
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Utility function to format time
 */
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Utility function to debounce function calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Utility function to throttle function calls
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Handle form submissions with loading states
 */
function handleFormSubmission(form) {
    form.addEventListener('submit', function(e) {
        if (form.checkValidity()) {
            showLoadingState(form);
        }
    });
}

/**
 * Initialize all forms with loading states
 */
function initializeFormLoadingStates() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        handleFormSubmission(form);
    });
}

/**
 * Update bus status indicators
 */
function updateBusStatus(busId, isReady) {
    const statusBadge = document.querySelector(`[data-bus-id="${busId}"] .status-badge`);
    if (statusBadge) {
        if (isReady) {
            statusBadge.className = 'badge bg-success status-badge';
            statusBadge.innerHTML = '<i class="fas fa-check-circle me-1"></i>Ready';
        } else {
            statusBadge.className = 'badge bg-warning status-badge';
            statusBadge.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Not Ready';
        }
    }
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Alt + S: Focus search
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            const searchInput = document.querySelector('.table-search');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Alt + N: Open add modal
        if (e.altKey && e.key === 'n') {
            e.preventDefault();
            const addButton = document.querySelector('[data-bs-toggle="modal"][data-bs-target*="add"]');
            if (addButton) {
                addButton.click();
            }
        }
        
        // Escape: Close modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            });
        }
    });
}

/**
 * Initialize responsive table handling
 */
function initializeResponsiveTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        // Add responsive wrapper if not already present
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

/**
 * Show route safeguarding alerts modal
 */
function showRouteSafeguardingAlerts(routeId, routeNumber) {
    // Get students data for this route
    fetch(`/api/route/${routeId}/safeguarding-alerts`)
        .then(response => response.json())
        .then(data => {
            let modalHtml = `
                <div class="modal fade" id="safeguardingAlertsModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-danger text-white">
                                <h5 class="modal-title">
                                    <i class="fas fa-shield-alt me-2"></i>Safeguarding Alerts - Route ${routeNumber}
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">`;
            
            data.students.forEach(student => {
                modalHtml += `
                    <div class="col-12 mb-3">
                        <div class="card border-danger">
                            <div class="card-header bg-danger text-white">
                                <h6 class="mb-0"><i class="fas fa-user me-2"></i>${student.name}</h6>
                            </div>
                            <div class="card-body">
                                <p class="mb-0">${student.safeguarding_notes || 'No specific notes available.'}</p>
                            </div>
                        </div>
                    </div>`;
            });
            
            modalHtml += `
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>`;
            
            // Remove existing modal if present
            const existingModal = document.getElementById('safeguardingAlertsModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add new modal to page
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('safeguardingAlertsModal'));
            modal.show();
            
            // Clean up when modal is hidden
            document.getElementById('safeguardingAlertsModal').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });
        })
        .catch(error => {
            console.error('Error fetching safeguarding alerts:', error);
            showToast('Error loading safeguarding alerts', 'error');
        });
}

/**
 * Show route pediatric first aid alerts modal
 */
function showRoutePediatricFirstAidAlerts(routeId, routeNumber) {
    // Get students data for this route
    fetch(`/api/route/${routeId}/pediatric-first-aid-alerts`)
        .then(response => response.json())
        .then(data => {
            let modalHtml = `
                <div class="modal fade" id="pediatricFirstAidAlertsModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">
                                    <i class="fas fa-user-md me-2"></i>Pediatric First Aid Requirements - Route ${routeNumber}
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">`;
            
            data.students.forEach(student => {
                modalHtml += `
                    <div class="col-12 mb-3">
                        <div class="card border-primary">
                            <div class="card-header bg-primary text-white">
                                <h6 class="mb-0"><i class="fas fa-user me-2"></i>${student.name}</h6>
                            </div>
                            <div class="card-body">
                                <p class="mb-0">
                                    <i class="fas fa-medical-bag me-2 text-primary"></i>
                                    Requires Pediatric First Aid qualified staff member
                                </p>
                                ${student.medical_notes ? `<small class="text-muted mt-2 d-block">${student.medical_notes}</small>` : ''}
                            </div>
                        </div>
                    </div>`;
            });
            
            modalHtml += `
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>`;
            
            // Remove existing modal if present
            const existingModal = document.getElementById('pediatricFirstAidAlertsModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add new modal to page
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('pediatricFirstAidAlertsModal'));
            modal.show();
            
            // Clean up when modal is hidden
            document.getElementById('pediatricFirstAidAlertsModal').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });
        })
        .catch(error => {
            console.error('Error fetching pediatric first aid alerts:', error);
            showToast('Error loading pediatric first aid alerts', 'error');
        });
}

/**
 * Initialize all functionality
 */
function initializeAllFeatures() {
    initializeFormLoadingStates();
    initializeKeyboardShortcuts();
    initializeResponsiveTables();
}

// Initialize additional features when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAllFeatures();
});

/**
 * Utility function to show loading state
 */
function showLoadingState(element) {
    element.classList.add('loading');
    element.disabled = true;
}

/**
 * Utility function to hide loading state
 */
function hideLoadingState(element) {
    element.classList.remove('loading');
    element.disabled = false;
}

/**
 * Cycle route status: Not Present → Arrived → Ready → Not Present
 */
function cycleRouteStatus(routeId, button) {
    // Prevent multiple rapid clicks - check if button is already processing
    if (button.disabled || button.dataset.processing === 'true') {
        console.log('Button click ignored - already processing');
        return;
    }
    
    // Mark button as processing FIRST to prevent sync interference
    button.dataset.processing = 'true';
    button.disabled = true;
    
    // Track this user's change to prevent sync conflicts
    if (typeof trackUserUpdate !== 'undefined') {
        trackUserUpdate(routeId);
    }
    
    const currentStatus = button.dataset.currentStatus;
    let newStatus;
    
    // Cycle through statuses
    switch(currentStatus) {
        case 'not_present':
            newStatus = 'arrived';
            break;
        case 'arrived':
            newStatus = 'ready';
            break;
        case 'ready':
            newStatus = 'not_present';
            break;
        default:
            newStatus = 'not_present';
    }
    
    // Track user action for real-time sync
    localStorage.setItem('lastUserAction', Date.now().toString());
    
    // Show loading state
    showLoadingState(button);
    
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || 
                      document.querySelector('input[name=csrf_token]')?.value;
    
    // Send AJAX request
    const formData = new FormData();
    if (csrfToken) {
        formData.append('csrf_token', csrfToken);
    }
    
    fetch(`/routes/${routeId}/cycle-status`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingState(button);
        
        if (data.success) {
            // Update button appearance
            button.dataset.currentStatus = data.status;
            
            // Update button classes
            button.className = `status-button btn btn-${data.status === 'ready' ? 'success' : data.status === 'arrived' ? 'warning' : 'danger'}`;
            
            // Update button text
            if (data.status === 'ready') {
                button.innerHTML = '<i class="fas fa-check-circle me-1"></i>Ready';
            } else if (data.status === 'arrived') {
                button.innerHTML = '<i class="fas fa-truck me-1"></i>Arrived';
            } else {
                button.innerHTML = '<i class="fas fa-times-circle me-1"></i>Not Present';
            }
            
            // Trigger audio notification for class accounts
            if (window.audioSystem && typeof window.audioSystem.onRouteStatusChange === 'function') {
                window.audioSystem.onRouteStatusChange();
            }
            
            // Show success message (skip if function doesn't exist)
            if (data.message && typeof showNotification === 'function') {
                showNotification(data.message, 'success');
            }
        } else {
            if (typeof showNotification === 'function') {
                showNotification(data.message || 'Failed to update route status', 'error');
            }
        }
    })
    .catch(error => {
        hideLoadingState(button);
        console.error('Error updating route status:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error updating route status', 'error');
        }
    })
    .finally(() => {
        // Manual refresh system - no cleanup needed
        
        // Re-enable button after a short delay to prevent rapid clicking
        setTimeout(() => {
            button.dataset.processing = 'false';
            button.disabled = false;
        }, 300);
    });
}

// Export functions for global use
window.HamiltonTransport = {
    showToast,
    formatNumber,
    formatDate,
    formatTime,
    updateBusStatus,
    showLoadingState,
    hideLoadingState,
    debounce,
    throttle
};
