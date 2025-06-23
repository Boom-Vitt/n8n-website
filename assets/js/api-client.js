/**
 * AI Video Uploader API Client
 * Handles communication between Netlify frontend and backend API
 */

class AIVideoUploaderAPI {
    constructor(baseURL = null, apiKey = null) {
        // Auto-detect backend URL based on environment
        if (baseURL) {
            this.baseURL = baseURL.replace(/\/$/, '');
        } else if (window.location.hostname === 'localhost') {
            this.baseURL = 'http://localhost:8001';
        } else {
            // Production - update with your actual backend URL
            this.baseURL = 'https://your-backend-url.railway.app';
        }
        
        this.apiKey = apiKey || this.getStoredApiKey();
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
        
        if (this.apiKey) {
            this.defaultHeaders['Authorization'] = `Bearer ${this.apiKey}`;
        }
    }
    
    /**
     * Get API key from localStorage
     */
    getStoredApiKey() {
        return localStorage.getItem('ai_video_uploader_api_key');
    }
    
    /**
     * Store API key in localStorage
     */
    setApiKey(apiKey) {
        this.apiKey = apiKey;
        localStorage.setItem('ai_video_uploader_api_key', apiKey);
        this.defaultHeaders['Authorization'] = `Bearer ${apiKey}`;
    }
    
    /**
     * Clear stored API key
     */
    clearApiKey() {
        this.apiKey = null;
        localStorage.removeItem('ai_video_uploader_api_key');
        delete this.defaultHeaders['Authorization'];
    }
    
    /**
     * Make API request with error handling
     */
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API Request failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    /**
     * Test API connection
     */
    async testConnection() {
        try {
            const result = await this.makeRequest('/api/health');
            return { success: true, data: result };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Upload video to TikTok
     */
    async uploadVideo(videoData) {
        const endpoint = this.apiKey 
            ? '/api/posts/video'
            : `/api/posts/video?api_key=${this.apiKey}`;
            
        return await this.makeRequest(endpoint, {
            method: 'POST',
            body: JSON.stringify(videoData)
        });
    }
    
    /**
     * Get user's connected platforms
     */
    async getConnectedPlatforms() {
        return await this.makeRequest('/auth/connected-platforms');
    }
    
    /**
     * Get OAuth URL for platform connection
     */
    async getOAuthURL(platform) {
        return await this.makeRequest(`/auth/oauth-url/${platform}`);
    }
    
    /**
     * Get user's posts
     */
    async getPosts() {
        return await this.makeRequest('/posts/');
    }
    
    /**
     * Approve a post
     */
    async approvePost(postId) {
        return await this.makeRequest(`/posts/${postId}/approve`, {
            method: 'POST'
        });
    }
    
    /**
     * Get supported platforms
     */
    async getSupportedPlatforms() {
        return await this.makeRequest('/platforms/');
    }
}

/**
 * UI Helper Functions
 */
class AIVideoUploaderUI {
    constructor(apiClient) {
        this.api = apiClient;
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Test connection button
        const testBtn = document.getElementById('test-connection-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testConnection());
        }
        
        // Upload form
        const uploadForm = document.getElementById('video-upload-form');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => this.handleVideoUpload(e));
        }
        
        // API key form
        const apiKeyForm = document.getElementById('api-key-form');
        if (apiKeyForm) {
            apiKeyForm.addEventListener('submit', (e) => this.handleApiKeySubmit(e));
        }
    }
    
    async testConnection() {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            statusEl.textContent = 'Testing connection...';
            statusEl.className = 'status testing';
        }
        
        const result = await this.api.testConnection();
        
        if (statusEl) {
            if (result.success) {
                statusEl.textContent = `✅ Connected to ${result.data.message}`;
                statusEl.className = 'status success';
            } else {
                statusEl.textContent = `❌ Connection failed: ${result.error}`;
                statusEl.className = 'status error';
            }
        }
    }
    
    async handleVideoUpload(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const videoData = {
            content: formData.get('content'),
            platforms: ['tiktok'], // Default to TikTok
            video_url: formData.get('video_url'),
            video_title: formData.get('video_title'),
            video_description: formData.get('video_description'),
            video_tags: formData.get('video_tags')?.split(',').map(tag => tag.trim()).filter(Boolean) || []
        };
        
        const submitBtn = event.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        try {
            submitBtn.textContent = 'Uploading...';
            submitBtn.disabled = true;
            
            const result = await this.api.uploadVideo(videoData);
            
            this.showMessage('✅ Video uploaded successfully! Check your TikTok drafts.', 'success');
            event.target.reset();
            
        } catch (error) {
            this.showMessage(`❌ Upload failed: ${error.message}`, 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }
    
    handleApiKeySubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const apiKey = formData.get('api_key');
        
        if (apiKey) {
            this.api.setApiKey(apiKey);
            this.showMessage('✅ API key saved successfully!', 'success');
            event.target.reset();
        }
    }
    
    showMessage(message, type = 'info') {
        // Create or update message element
        let messageEl = document.getElementById('api-message');
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.id = 'api-message';
            document.body.appendChild(messageEl);
        }
        
        messageEl.textContent = message;
        messageEl.className = `message ${type}`;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageEl.style.opacity = '0';
            setTimeout(() => messageEl.remove(), 300);
        }, 5000);
    }
}

/**
 * Initialize when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize API client
    window.aiVideoAPI = new AIVideoUploaderAPI();
    window.aiVideoUI = new AIVideoUploaderUI(window.aiVideoAPI);
    
    // Auto-test connection if API key is available
    if (window.aiVideoAPI.apiKey) {
        window.aiVideoUI.testConnection();
    }
});

/**
 * CSS for messages (inject into page)
 */
const messageStyles = `
<style>
.message {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    z-index: 10000;
    transition: opacity 0.3s ease;
}
.message.success { background: #22C55E; }
.message.error { background: #EF4444; }
.message.info { background: #3B82F6; }
.status.testing { color: #F59E0B; }
.status.success { color: #22C55E; }
.status.error { color: #EF4444; }
</style>
`;

document.head.insertAdjacentHTML('beforeend', messageStyles);
