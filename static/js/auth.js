// Authentication JavaScript for Google SSO

// API Base URL
const API_BASE = window.location.origin;

// Store token in localStorage
function setToken(token) {
    localStorage.setItem('access_token', token);
}

function getToken() {
    return localStorage.getItem('access_token');
}

function removeToken() {
    localStorage.removeItem('access_token');
}

// Show loading modal
function showLoading() {
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
}

function hideLoading() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
    if (modal) modal.hide();
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
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert-floating');
        if (alert) alert.remove();
    }, 5000);
}

// Google Sign-In callback (called by Google Identity Services)
async function handleGoogleSignIn(response) {
    console.log('Google Sign-In response:', response);
    showLoading();
    
    try {
        // Send the Google credential to our backend
        const apiResponse = await fetch(`${API_BASE}/auth/sso`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token: response.credential, // This is the ID token from Google
                provider: 'google'
            })
        });
        
        const data = await apiResponse.json();
        
        if (apiResponse.ok) {
            setToken(data.access_token);
            
            // Store user info
            localStorage.setItem('user_info', JSON.stringify(data.user));
            
            showAlert('Successfully logged in with Google!', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            showAlert(data.detail || 'Google login failed', 'danger');
        }
    } catch (error) {
        showAlert('Network error during Google login', 'danger');
        console.error('Google login error:', error);
    } finally {
        hideLoading();
    }
}

// Alternative Google OAuth (redirect flow)
function loginWithGoogleOAuth() {
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=460911215496-mlekdrb7o66a0ksg2c46lpb4gi3m4rdr.apps.googleusercontent.com&` +
        `redirect_uri=${encodeURIComponent(window.location.origin + '/auth/google/callback')}&` +
        `response_type=code&` +
        `scope=openid email profile&` +
        `access_type=offline&` +
        `prompt=consent`;
    
    window.location.href = googleAuthUrl;
}

// Development mode login (bypasses Google OAuth)
async function loginDevelopmentMode() {
    showLoading();
    
    try {
        // Create a mock user for development
        const mockUserData = {
            access_token: 'dev_token_' + Date.now(),
            user: {
                id: 1,
                username: 'dev_user',
                email: 'dev@example.com',
                connected_platforms: {
                    facebook: false,
                    instagram: false,
                    tiktok: false,
                    youtube: false
                }
            }
        };
        
        // Store the mock data
        setToken(mockUserData.access_token);
        localStorage.setItem('user_info', JSON.stringify(mockUserData.user));
        
        showAlert('Development mode login successful!', 'success');
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 1000);
        
    } catch (error) {
        showAlert('Development login failed', 'danger');
        console.error('Dev login error:', error);
    } finally {
        hideLoading();
    }
}

// Fallback Google OAuth (manual implementation)
async function loginWithGoogleFallback() {
    showAlert('Please use the Google Sign-In button above', 'info');
}

// Initialize Google Sign-In
function initializeGoogleSignIn() {
    // Check if Google Identity Services loaded
    if (typeof google !== 'undefined' && google.accounts) {
        console.log('Google Identity Services loaded successfully');
        
        // Update the client ID in the HTML
        const clientIdElement = document.getElementById('g_id_onload');
        if (clientIdElement) {
            // You'll need to replace this with your actual Google Client ID
            const googleClientId = '460911215496-mlekdrb7o66a0ksg2c46lpb4gi3m4rdr.apps.googleusercontent.com';
            clientIdElement.setAttribute('data-client_id', googleClientId);
        }
    } else {
        console.log('Google Identity Services not loaded, showing fallback button');
        // Show fallback button if Google Identity Services doesn't load
        const fallbackBtn = document.getElementById('fallbackBtn');
        if (fallbackBtn) {
            fallbackBtn.style.display = 'block';
        }
    }
}

// Check if user is already logged in
function checkAuthStatus() {
    const token = getToken();
    if (token && window.location.pathname === '/login') {
        window.location.href = '/dashboard';
    }
}

// Logout function
function logout() {
    removeToken();
    localStorage.removeItem('user_info');
    localStorage.removeItem('api_key_info');
    showAlert('Logged out successfully', 'success');
    setTimeout(() => {
        window.location.href = '/login';
    }, 1000);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    initializeGoogleSignIn();
});

// Handle Google Identity Services load
window.addEventListener('load', () => {
    // Give Google Identity Services time to load
    setTimeout(initializeGoogleSignIn, 1000);
});