// Real-time updates using lightweight polling
class RealTimeUpdater {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.pollInterval = 5000; // 5 seconds - reduced frequency to prevent interference
        this.lastUpdate = 0;
        this.pollTimer = null;
        this.isPolling = false;
        
        this.init();
    }
    
    getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('/routes')) return 'routes';
        if (path.includes('/dashboard')) return 'dashboard';
        if (path.includes('/students')) return 'students';
        if (path.includes('/staff')) return 'staff';
        if (path.includes('/schools')) return 'schools';
        return 'general';
    }
    
    init() {
        // Enable real-time polling only for Transport Check-in page (routes)
        if (this.currentPage === 'routes') {
            console.log('Real-time sync enabled for Transport Check-in page');
            this.startPolling();
        } else {
            console.log('Real-time sync disabled for', this.currentPage, '- manual refresh required');
            this.stopPolling();
        }
    }
    
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.poll();
        this.showConnectionStatus('connected');
    }
    
    async poll() {
        if (!this.isPolling) return;
        
        try {
            const response = await fetch(`/api/sync/${this.currentPage}?last_update=${this.lastUpdate}`);
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    this.handleSyncData(data);
                    this.lastUpdate = data.timestamp;
                }
            }
        } catch (error) {
            console.error('Polling error:', error);
            this.showConnectionStatus('disconnected');
        }
        
        // Schedule next poll
        if (this.isPolling) {
            this.pollTimer = setTimeout(() => this.poll(), this.pollInterval);
        }
    }
    
    stopPolling() {
        this.isPolling = false;
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }
    

    
    handleSyncData(data) {
        // For routes page, check if any route status has changed
        if (this.currentPage === 'routes' && data.routes_updated) {
            console.log('Route status changes detected from other devices - refreshing page');
            // Force page reload to show latest route statuses
            window.location.reload(true);
            return;
        }
        if (this.currentPage === 'routes' && data.routes) {
            this.updateRouteData(data.routes);
            
            // Check if routes list needs refresh (new routes added)
            if (data.needs_refresh) {
                this.refreshRoutesPage();
            }
        } else if (this.currentPage === 'students' && data.needs_refresh) {
            this.refreshStudentsPage();
        }
    }
    
    updateRouteData(routes) {
        let hasChanges = false;
        
        for (const [routeId, routeData] of Object.entries(routes)) {
            const row = document.querySelector(`input[value="${routeId}"]`)?.closest('tr');
            if (row) {
                // Check if status changed
                const statusCell = row.cells[2];
                const statusButton = statusCell?.querySelector('.status-button');
                
                if (statusButton) {
                    const currentClass = statusButton.className;
                    const newClass = `status-button btn btn-${routeData.status_color}`;
                    
                    if (currentClass !== newClass) {
                        hasChanges = true;
                        statusButton.className = newClass;
                        statusButton.dataset.currentStatus = routeData.status;
                        
                        if (routeData.status === 'ready') {
                            statusButton.innerHTML = '<i class="fas fa-check-circle me-1"></i>Ready';
                        } else if (routeData.status === 'arrived') {
                            statusButton.innerHTML = '<i class="fas fa-truck me-1"></i>Arrived';
                        } else {
                            statusButton.innerHTML = '<i class="fas fa-times-circle me-1"></i>Not Present';
                        }
                    }
                }
                
            }
        }
        
        // Only show notification if changes detected AND not from current user
        if (hasChanges && !this.isUserAction()) {
            console.log('Routes updated from another device - changes detected');
            // Keep notifications disabled but log the sync for debugging
        }
    }
    
    async refreshStudentsPage() {
        // Only refresh if not a user action (to avoid refreshing after own uploads)
        if (!this.isUserAction()) {
            // this.showNotification('Students list updated', 'info'); // Disabled - too intrusive
            // Smooth content update instead of full page refresh
            await this.updateStudentsContent();
        }
    }
    
    async refreshRoutesPage() {
        // Always refresh when routes are updated (could be from CSV upload on different page)
        // this.showNotification('Routes list updated', 'info'); // Disabled - too intrusive
        // Smooth content update instead of full page refresh
        await this.updateRoutesContent();
    }
    
    async updateStudentsContent() {
        try {
            // Fetch the updated students page content
            const response = await fetch(window.location.href);
            if (response.ok) {
                const html = await response.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                // Update the students table content
                const newTableBody = doc.querySelector('table tbody');
                const currentTableBody = document.querySelector('table tbody');
                
                if (newTableBody && currentTableBody) {
                    // Smooth fade transition
                    currentTableBody.style.opacity = '0.5';
                    
                    setTimeout(() => {
                        // Safe DOM manipulation: Clear and clone nodes instead of innerHTML
                        while (currentTableBody.firstChild) {
                            currentTableBody.removeChild(currentTableBody.firstChild);
                        }
                        
                        // Clone all child nodes from the new content
                        const children = Array.from(newTableBody.children);
                        children.forEach(child => {
                            currentTableBody.appendChild(child.cloneNode(true));
                        });
                        
                        currentTableBody.style.opacity = '1';
                        
                        // Re-initialize any event listeners for new content
                        this.initializeStudentEvents();
                    }, 200);
                }
            }
        } catch (error) {
            console.error('Error updating students content:', error);
            // Fallback to page refresh if smooth update fails
            window.location.reload();
        }
    }
    
    async updateRoutesContent() {
        try {
            // Fetch the updated routes page content
            const response = await fetch(window.location.href);
            if (response.ok) {
                const html = await response.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                // Update the routes table content
                const newTableBody = doc.querySelector('table tbody');
                const currentTableBody = document.querySelector('table tbody');
                
                if (newTableBody && currentTableBody) {
                    // Smooth fade transition
                    currentTableBody.style.opacity = '0.5';
                    
                    setTimeout(() => {
                        // Safe DOM manipulation: Clear and clone nodes instead of innerHTML
                        while (currentTableBody.firstChild) {
                            currentTableBody.removeChild(currentTableBody.firstChild);
                        }
                        
                        // Clone all child nodes from the new content
                        const children = Array.from(newTableBody.children);
                        children.forEach(child => {
                            currentTableBody.appendChild(child.cloneNode(true));
                        });
                        
                        currentTableBody.style.opacity = '1';
                        
                        // Re-initialize any event listeners for new content
                        this.initializeRouteEvents();
                    }, 200);
                }
            }
        } catch (error) {
            console.error('Error updating routes content:', error);
            // Fallback to page refresh if smooth update fails
            window.location.reload();
        }
    }
    
    initializeStudentEvents() {
        // Re-initialize checkbox events for bulk selection
        const checkboxes = document.querySelectorAll('.student-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                if (typeof updateBulkActions === 'function') {
                    updateBulkActions();
                }
            });
        });
        
        // Note: Using button-based select all system now - no checkbox events needed
    }
    
    initializeRouteEvents() {
        // Re-initialize checkbox events for bulk selection
        const checkboxes = document.querySelectorAll('.route-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                if (typeof updateBulkButtons === 'function') {
                    updateBulkButtons();
                }
            });
        });
        
        // Note: Using button-based select all system now - no checkbox events needed
    }
    

    
    isUserAction() {
        // Check if there's a recent user action (within last 10 seconds to be more conservative)
        const lastAction = parseInt(localStorage.getItem('lastUserAction') || '0');
        const now = Date.now();
        const isRecent = (now - lastAction) < 10000;
        if (isRecent) {
            console.log('Recent user action detected, skipping notifications');
        }
        return isRecent;
    }
    
    showConnectionStatus(status) {
        // Show connection status indicator
        let indicator = document.getElementById('connection-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'connection-indicator';
            indicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded shadow-sm';
            indicator.style.zIndex = '9999';
            document.body.appendChild(indicator);
        }
        
        switch (status) {
            case 'connected':
                indicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded shadow-sm bg-success text-white';
                // Clear and rebuild content safely
                indicator.textContent = '';
                const connectedIcon = document.createElement('i');
                connectedIcon.className = 'fas fa-wifi me-1';
                indicator.appendChild(connectedIcon);
                indicator.appendChild(document.createTextNode('Connected'));
                setTimeout(() => indicator.style.display = 'none', 3000);
                break;
            case 'disconnected':
                indicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded shadow-sm bg-warning text-dark';
                // Clear and rebuild content safely
                indicator.textContent = '';
                const disconnectedIcon = document.createElement('i');
                disconnectedIcon.className = 'fas fa-wifi me-1';
                indicator.appendChild(disconnectedIcon);
                indicator.appendChild(document.createTextNode('Reconnecting...'));
                indicator.style.display = 'block';
                break;
            case 'failed':
                indicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded shadow-sm bg-danger text-white';
                // Clear and rebuild content safely
                indicator.textContent = '';
                const failedIcon = document.createElement('i');
                failedIcon.className = 'fas fa-exclamation-triangle me-1';
                indicator.appendChild(failedIcon);
                indicator.appendChild(document.createTextNode('Connection Failed'));
                indicator.style.display = 'block';
                break;
        }
    }
    
    showNotification(message, type = 'info') {
        // Create a toast notification
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        
        // Build toast structure safely using DOM methods
        const flexDiv = document.createElement('div');
        flexDiv.className = 'd-flex';
        
        const toastBody = document.createElement('div');
        toastBody.className = 'toast-body';
        
        // Create icon element safely
        const icon = document.createElement('i');
        icon.className = 'fas fa-sync-alt me-2';
        
        // Add icon and message text safely
        toastBody.appendChild(icon);
        toastBody.appendChild(document.createTextNode(message));
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close btn-close-white me-2 m-auto';
        closeButton.setAttribute('data-bs-dismiss', 'toast');
        
        flexDiv.appendChild(toastBody);
        flexDiv.appendChild(closeButton);
        toast.appendChild(flexDiv);
        
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }
}

// COMPLETELY DISABLED: Real-time sync was unreliable
// document.addEventListener('DOMContentLoaded', () => {
//     window.realTimeUpdater = new RealTimeUpdater();
// });