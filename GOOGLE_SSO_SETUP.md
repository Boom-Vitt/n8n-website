# 🔑 Google SSO Setup Guide

## ❌ Current Issue: "Continue with Google" Not Working

The Google Sign-In button isn't showing a popup because you need to:

### 1. **Get Google OAuth Credentials**

Go to [Google Cloud Console](https://console.cloud.google.com/):

1. **Create/Select Project**
2. **Enable APIs:**
   - Google+ API
   - Google Identity Services
3. **Create OAuth 2.0 Credentials:**
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Web application"
   - **Authorized origins:** 
     ```
     http://localhost:8000
     http://localhost:8001
     https://yourdomain.com
     ```
   - **Authorized redirect URIs:**
     ```
     http://localhost:8000/auth/callback/google
     ```

4. **Copy Client ID** (looks like: `123456789-abc123.apps.googleusercontent.com`)

### 2. **Update Your .env File**

```bash
# Copy example file
cp .env.example .env

# Edit .env file and add:
GOOGLE_CLIENT_ID=123456789-abc123.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 3. **Update Login Template**

Edit `templates/login.html` line 42:
```html
<!-- Change this line: -->
data-client_id="YOUR_GOOGLE_CLIENT_ID"

<!-- To your actual Client ID: -->
data-client_id="123456789-abc123.apps.googleusercontent.com"
```

### 4. **Test the Flow**

1. **Start your app:**
   ```bash
   python -m app.main
   ```

2. **Visit:** `http://localhost:8000/login`

3. **Click "Sign in with Google"** → Should open Google popup

4. **After login:** Redirects to dashboard with platform connections

---

## 🧪 **Quick Test Without Google Setup**

If you want to test the platform connections immediately, you can temporarily use mock authentication:

### Option A: Create Test User Directly
```bash
# Open Python shell
python

# Create test user
from app.database import SessionLocal
from app.models import User
import secrets

db = SessionLocal()
user = User(
    username="testuser",
    email="test@example.com", 
    google_id="123456789",
    hashed_password="dummy"
)
db.add(user)
db.commit()
print("Test user created!")
```

### Option B: Modify Frontend for Testing
Edit `static/js/auth.js` line 60 to use a test token:
```javascript
body: JSON.stringify({
    token: "test_token_12345",  // Use this for testing
    provider: 'google'
})
```

---

## ✅ **Once Google SSO Works:**

Users can:
1. ✅ **Sign in with Google**
2. ✅ **See dashboard with 4 platform cards**
3. ✅ **Click "Connect" on TikTok/YouTube**
4. ✅ **Complete OAuth flows**
5. ✅ **Generate API keys**
6. ✅ **Use with n8n**

---

## 🐛 **Troubleshooting:**

**Google Sign-In Button Not Showing:**
- Check browser console for errors
- Verify Google Client ID is correct
- Ensure domain is authorized in Google Console

**"Invalid token" Error:**
- Check Google Client ID matches your app
- Verify token is not expired
- Check network requests in browser dev tools

**Need Help?**
The Google Client ID is the key piece you're missing! Get it from Google Cloud Console and everything will work! 🚀