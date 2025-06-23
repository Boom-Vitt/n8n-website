// Dashboard JavaScript

const API_BASE = window.location.origin;

// Get stored token
function getToken() {
    return localStorage.getItem('access_token');
}

// Get stored user info
function getUserInfo() {
    const userInfo = localStorage.getItem('user_info');
    return userInfo ? JSON.parse(userInfo) : null;
}

// API call helper
async function apiCall(endpoint, options = {}) {
    const token = getToken();
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
        }
    };
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...defaultOptions,
        ...options
    });
    
    if (response.status === 401) {
        logout();
        return;
    }
    
    return response;
}

// Show alert
function showAlert(message, type = 'success') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible alert-floating fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', alertHtml);
    
    setTimeout(() => {
        const alert = document.querySelector('.alert-floating');
        if (alert) alert.remove();
    }, 5000);
}

// Load user information
async function loadUserInfo() {
    const userInfo = getUserInfo();
    if (userInfo) {
        document.getElementById('username').textContent = userInfo.username;
        document.getElementById('userDisplayName').textContent = userInfo.name;
        document.getElementById('userEmail').textContent = userInfo.email;
        return;
    }
    
    try {
        const response = await apiCall('/auth/me');
        if (response && response.ok) {
            const data = await response.json();
            document.getElementById('username').textContent = data.username;
            document.getElementById('userDisplayName').textContent = data.username;
            document.getElementById('userEmail').textContent = data.email;
        }
    } catch (error) {
        console.error('Failed to load user info:', error);
    }
}

// Load API key status
async function loadApiKeyStatus() {
    try {
        const response = await apiCall('/auth/api-key-status');
        if (response && response.ok) {
            const data = await response.json();
            
            if (data.has_api_key && data.api_key_active) {
                showApiKeySection(data);
            } else {
                showNoApiKeySection();
            }
        }
    } catch (error) {
        console.error('Failed to load API key status:', error);
        showNoApiKeySection();
    }
}

// Show API key section
function showApiKeySection(data) {
    document.getElementById('noApiKey').classList.add('d-none');
    document.getElementById('apiKeySection').classList.remove('d-none');
    document.getElementById('generateBtn').innerHTML = '<i class="fas fa-sync"></i> Regenerate';
    
    // Mask API key for security
    const maskedKey = data.api_key ? `${data.api_key.substring(0, 8)}...${data.api_key.substring(data.api_key.length - 8)}` : 'Hidden for security';
    document.getElementById('apiKeyDisplay').value = maskedKey;
    
    document.getElementById('apiKeyCreated').textContent = data.created_at ? new Date(data.created_at).toLocaleDateString() : '-';
    document.getElementById('apiKeyLastUsed').textContent = data.last_used ? new Date(data.last_used).toLocaleDateString() : 'Never';
    
    // Enable buttons
    document.getElementById('connectionGuideBtn').disabled = false;
    document.getElementById('testBtn').disabled = false;
    
    // Store full API key for connection guide
    if (data.api_key) {
        localStorage.setItem('api_key_info', JSON.stringify(data));
    }
}

// Show no API key section
function showNoApiKeySection() {
    document.getElementById('noApiKey').classList.remove('d-none');
    document.getElementById('apiKeySection').classList.add('d-none');
    document.getElementById('generateBtn').innerHTML = '<i class="fas fa-plus"></i> Generate API Key';
    
    // Disable buttons
    document.getElementById('connectionGuideBtn').disabled = true;
    document.getElementById('testBtn').disabled = true;
}

// Load platform connections
async function loadPlatformConnections() {
    try {
        const response = await apiCall('/auth/connected-platforms');
        if (response && response.ok) {
            const data = await response.json();
            
            updatePlatformStatus('tiktok', data.tiktok);
            updatePlatformStatus('youtube', data.youtube);
            updatePlatformStatus('facebook', data.facebook);
            updatePlatformStatus('instagram', data.instagram);
        }
    } catch (error) {
        console.error('Failed to load platform connections:', error);
    }
}

// Update platform connection status
function updatePlatformStatus(platform, connected) {
    const statusElement = document.getElementById(`${platform}Status`);
    const btnElement = document.getElementById(`${platform}Btn`);
    const cardElement = document.getElementById(`${platform}Card`);
    
    if (connected) {
        statusElement.textContent = 'Connected';
        statusElement.className = 'badge bg-success';
        btnElement.textContent = 'Disconnect';
        btnElement.className = 'btn btn-sm btn-outline-danger';
        btnElement.onclick = () => disconnectPlatform(platform);
        cardElement.classList.add('border-success');
    } else {
        statusElement.textContent = 'Not Connected';
        statusElement.className = 'badge bg-secondary';
        btnElement.textContent = 'Connect';
        btnElement.className = 'btn btn-sm btn-outline-primary';
        btnElement.onclick = () => connectPlatform(platform);
        cardElement.classList.remove('border-success');
    }
}

// Connect to social media platform
async function connectPlatform(platform) {
    try {
        const response = await apiCall(`/auth/oauth-url/${platform}`);
        if (response && response.ok) {
            const data = await response.json();
            // Open OAuth URL in a popup window
            const popup = window.open(
                data.oauth_url,
                `connect_${platform}`,
                'width=600,height=700,scrollbars=yes,resizable=yes'
            );
            
            // Listen for popup to close (user completed OAuth)
            const checkClosed = setInterval(() => {
                if (popup.closed) {
                    clearInterval(checkClosed);
                    // Refresh platform connections after a short delay
                    setTimeout(() => {
                        loadPlatformConnections();
                        showAlert(`${platform.charAt(0).toUpperCase() + platform.slice(1)} connection completed! Please check the status.`, 'info');
                    }, 2000);
                }
            }, 1000);
            
        } else {
            showAlert(`Failed to get ${platform} connection URL`, 'danger');
        }
    } catch (error) {
        showAlert('Network error. Please try again.', 'danger');
        console.error(`${platform} connection error:`, error);
    }
}

// Disconnect from social media platform
async function disconnectPlatform(platform) {
    if (!confirm(`Are you sure you want to disconnect from ${platform.charAt(0).toUpperCase() + platform.slice(1)}?`)) {
        return;
    }
    
    try {
        const response = await apiCall(`/auth/disconnect-platform?platform=${platform}`, {
            method: 'POST'
        });
        
        if (response && response.ok) {
            showAlert(`${platform.charAt(0).toUpperCase() + platform.slice(1)} disconnected successfully`, 'success');
            updatePlatformStatus(platform, false);
        } else {
            const errorData = await response.json();
            showAlert(errorData.detail || `Failed to disconnect ${platform}`, 'danger');
        }
    } catch (error) {
        showAlert('Network error. Please try again.', 'danger');
        console.error(`${platform} disconnection error:`, error);
    }
}

// Load usage statistics
async function loadUsageStats() {
    try {
        const response = await apiCall('/auth/api-key-stats');
        if (response && response.ok) {
            const data = await response.json();
            
            document.getElementById('totalCalls').textContent = data.total_usage || 0;
            document.getElementById('successRate').textContent = `${data.success_rate || 0}%`;
            document.getElementById('recentCalls').textContent = data.recent_usage_30_days || 0;
        }
    } catch (error) {
        console.error('Failed to load usage stats:', error);
    }
}

// Generate API key
function generateApiKey() {
    const modal = new bootstrap.Modal(document.getElementById('apiKeyModal'));
    modal.show();
}

// Confirm API key generation
async function confirmGenerateApiKey() {
    const name = document.getElementById('apiKeyName').value || 'n8n Integration Key';
    const modal = bootstrap.Modal.getInstance(document.getElementById('apiKeyModal'));
    
    try {
        const response = await apiCall('/auth/generate-api-key', {
            method: 'POST',
            body: JSON.stringify({ name: name })
        });
        
        if (response && response.ok) {
            const data = await response.json();
            showAlert('API key generated successfully!', 'success');
            modal.hide();
            
            // Store the full API key temporarily for showing
            localStorage.setItem('api_key_info', JSON.stringify({
                api_key: data.api_key,
                name: data.name,
                created_at: data.created_at,
                is_active: data.is_active
            }));
            
            // Show the actual key for a moment
            document.getElementById('apiKeyDisplay').value = data.api_key;
            showApiKeySection({
                api_key: data.api_key,
                created_at: data.created_at,
                last_used: null
            });
            
            // Mask it after 10 seconds
            setTimeout(() => {
                const maskedKey = `${data.api_key.substring(0, 8)}...${data.api_key.substring(data.api_key.length - 8)}`;
                document.getElementById('apiKeyDisplay').value = maskedKey;
            }, 10000);
            
        } else {
            const errorData = await response.json();
            showAlert(errorData.detail || 'Failed to generate API key', 'danger');
        }
    } catch (error) {
        showAlert('Network error. Please try again.', 'danger');
        console.error('API key generation error:', error);
    }
}

// Copy API key to clipboard
async function copyApiKey() {
    const apiKeyInfo = localStorage.getItem('api_key_info');
    if (!apiKeyInfo) {
        showAlert('API key not available', 'warning');
        return;
    }
    
    const keyData = JSON.parse(apiKeyInfo);
    if (keyData.api_key) {
        try {
            await navigator.clipboard.writeText(keyData.api_key);
            showAlert('API key copied to clipboard!', 'success');
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = keyData.api_key;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showAlert('API key copied to clipboard!', 'success');
        }
    }
}

// Revoke API key
async function revokeApiKey() {
    if (!confirm('Are you sure you want to revoke your API key? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await apiCall('/auth/revoke-api-key', {
            method: 'POST'
        });
        
        if (response && response.ok) {
            showAlert('API key revoked successfully', 'success');
            localStorage.removeItem('api_key_info');
            showNoApiKeySection();
            loadUsageStats(); // Refresh stats
        } else {
            const errorData = await response.json();
            showAlert(errorData.detail || 'Failed to revoke API key', 'danger');
        }
    } catch (error) {
        showAlert('Network error. Please try again.', 'danger');
        console.error('API key revocation error:', error);
    }
}

// Get connection guide
async function getConnectionGuide() {
    try {
        const response = await apiCall('/n8n/connection-guide');
        if (response && response.ok) {
            const data = await response.json();
            displayConnectionGuide(data);
        } else {
            showAlert('Failed to load connection guide', 'danger');
        }
    } catch (error) {
        showAlert('Network error. Please try again.', 'danger');
        console.error('Connection guide error:', error);
    }
}

// Display connection guide in modal
function displayConnectionGuide(data) {
    const content = `
        <div class="mb-4">
            <h6>Your API Key</h6>
            <div class="input-group">
                <input type="text" class="form-control font-monospace" value="${data.api_key}" readonly>
                <button class="btn btn-outline-secondary" onclick="copyText('${data.api_key}')">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
        
        <div class="mb-4">
            <h6>Endpoints</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tbody>
                        <tr>
                            <td><strong>Video Post:</strong></td>
                            <td><code>${data.endpoints.create_video_post}</code></td>
                        </tr>
                        <tr>
                            <td><strong>Webhook:</strong></td>
                            <td><code>${data.endpoints.webhook_upload}</code></td>
                        </tr>
                        <tr>
                            <td><strong>Test:</strong></td>
                            <td><code>${data.base_url}/n8n/test-connection</code></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="mb-4">
            <h6>Example n8n HTTP Request</h6>
            <pre class="bg-dark text-light p-3 rounded"><code>${JSON.stringify(data.example_requests.webhook_upload, null, 2)}</code></pre>
        </div>
        
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            <strong>Quick Setup:</strong> Copy your API key and the webhook URL above into your n8n HTTP Request node.
        </div>
    `;
    
    document.getElementById('connectionGuideContent').innerHTML = content;
    const modal = new bootstrap.Modal(document.getElementById('connectionGuideModal'));
    modal.show();
}

// Copy text helper
async function copyText(text) {
    try {
        await navigator.clipboard.writeText(text);
        showAlert('Copied to clipboard!', 'success');
    } catch (err) {
        console.error('Copy failed:', err);
    }
}

// Test API connection
async function testConnection() {
    const apiKeyInfo = localStorage.getItem('api_key_info');
    if (!apiKeyInfo) {
        showAlert('No API key available', 'warning');
        return;
    }
    
    const keyData = JSON.parse(apiKeyInfo);
    const testBtn = document.getElementById('testBtn');
    const originalText = testBtn.innerHTML;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    testBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/n8n/test-connection?api_key=${keyData.api_key}`);
        
        if (response.ok) {
            const data = await response.json();
            showAlert('API connection test successful!', 'success');
        } else {
            showAlert('API connection test failed', 'danger');
        }
    } catch (error) {
        showAlert('Network error during test', 'danger');
        console.error('Test connection error:', error);
    } finally {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    }
}

// View detailed usage stats
function viewUsageStats() {
    showAlert('Detailed analytics would open here', 'info');
    // In a real implementation, this would open a detailed analytics page
}

// Download connection guide
function downloadGuide() {
    const content = document.getElementById('connectionGuideContent').innerText;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'n8n-connection-guide.txt';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    showAlert('Guide downloaded!', 'success');
}

// Logout function
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('api_key_info');
    window.location.href = '/login';
}

// Check authentication
function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Initialize dashboard
async function initDashboard() {
    if (!checkAuth()) return;
    
    await loadUserInfo();
    await loadPlatformConnections();
    await loadApiKeyStatus();
    await loadUsageStats();
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initDashboard);