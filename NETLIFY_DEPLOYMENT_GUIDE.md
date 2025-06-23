# 🚀 Netlify Deployment Guide for AI Video Uploader

## 🎯 Current Architecture

Your project has **two components**:
1. **Static Website** (Portfolio + Info Pages) → Netlify ✅
2. **Python Backend** (AI Video Uploader API) → Needs separate hosting ❌

## 🔧 Deployment Strategy: Hybrid Architecture

### **Frontend (Netlify) - CURRENT**
- ✅ `index.html` - BoomBigNose portfolio
- ✅ `ai-video-uploader.html` - Tool information page
- ✅ `assets/` - Static files
- ✅ Custom domain support
- ✅ SSL certificates
- ✅ CDN distribution

### **Backend (Separate Hosting) - NEEDED**
- 🔄 Python FastAPI application
- 🔄 TikTok API integration
- 🔄 Database (SQLite/PostgreSQL)
- 🔄 Background tasks (Celery + Redis)
- 🔄 File management system

## 🌐 Backend Hosting Options

### **Option 1: Railway (Recommended)**
**Why Railway:**
- ✅ Easy Python deployment
- ✅ Built-in PostgreSQL
- ✅ Redis support
- ✅ Environment variables
- ✅ Automatic deployments
- ✅ Free tier available

**Setup:**
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and deploy
railway login
railway init
railway up
```

### **Option 2: Render**
**Why Render:**
- ✅ Free tier for web services
- ✅ PostgreSQL support
- ✅ Redis support
- ✅ GitHub integration

### **Option 3: Heroku**
**Why Heroku:**
- ✅ Mature platform
- ✅ Add-ons ecosystem
- ✅ Easy scaling

### **Option 4: DigitalOcean App Platform**
**Why DigitalOcean:**
- ✅ Competitive pricing
- ✅ Database support
- ✅ Easy deployment

## 📁 Repository Structure Reorganization

### **Current Structure:**
```
n8n-website/
├── index.html              # Static site
├── ai-video-uploader.html  # Static site
├── assets/                 # Static site
├── app/                    # Python backend
├── requirements.txt        # Python backend
└── ...
```

### **Recommended Structure:**
```
n8n-website/
├── frontend/               # Netlify deployment
│   ├── index.html
│   ├── ai-video-uploader.html
│   ├── assets/
│   └── netlify.toml
├── backend/                # Separate hosting
│   ├── app/
│   ├── requirements.txt
│   ├── Procfile
│   └── railway.toml
└── README.md
```

## 🔄 Migration Steps

### **Step 1: Reorganize Repository**
```bash
# Create directories
mkdir frontend backend

# Move static files to frontend
mv index.html frontend/
mv ai-video-uploader.html frontend/
mv assets frontend/

# Move Python app to backend
mv app backend/
mv requirements.txt backend/
mv migrate_db.py backend/
mv test_tiktok_integration.py backend/
```

### **Step 2: Configure Netlify**
Create `frontend/netlify.toml`:
```toml
[build]
  publish = "."

[[redirects]]
  from = "/api/*"
  to = "https://your-backend-url.railway.app/api/:splat"
  status = 200
  force = true

[build.environment]
  NODE_VERSION = "18"
```

### **Step 3: Configure Backend for Railway**
Create `backend/railway.toml`:
```toml
[build]
  builder = "NIXPACKS"

[deploy]
  startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"

[variables]
  PYTHONPATH = "/app"
```

Create `backend/Procfile`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.scheduler.celery_app worker --loglevel=info
```

### **Step 4: Update Frontend to Use Backend API**
Update your static site to point to the backend API:

```javascript
// In your frontend JavaScript
const API_BASE_URL = 'https://your-backend-url.railway.app';

// Example API call
async function uploadVideo(videoData) {
    const response = await fetch(`${API_BASE_URL}/api/posts/video`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(videoData)
    });
    return response.json();
}
```

## 🔐 Environment Configuration

### **Backend Environment Variables (Railway/Render):**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# TikTok API
TIKTOK_CLIENT_KEY=your-key
TIKTOK_CLIENT_SECRET=your-secret

# Redis
REDIS_URL=redis://user:pass@host:port

# CORS (allow your Netlify domain)
CORS_ORIGINS=https://your-site.netlify.app,https://boombignose.com

# Security
SECRET_KEY=your-secret-key
```

### **Frontend Environment (Netlify):**
```bash
# Build environment
NODE_VERSION=18
PYTHON_VERSION=3.11
```

## 🚀 Deployment Commands

### **Deploy Frontend to Netlify:**
```bash
# Already deployed - just update files
git add frontend/
git commit -m "Reorganize for hybrid deployment"
git push origin main
```

### **Deploy Backend to Railway:**
```bash
cd backend
railway login
railway init
railway up

# Set environment variables
railway variables set DATABASE_URL=postgresql://...
railway variables set TIKTOK_CLIENT_KEY=your-key
# ... etc
```

## 🔗 Integration Points

### **Frontend → Backend Communication:**
1. **API Calls**: Frontend makes AJAX calls to backend
2. **CORS**: Backend configured to allow Netlify domain
3. **Authentication**: API keys or JWT tokens
4. **Error Handling**: Graceful fallbacks in frontend

### **n8n → Backend Integration:**
1. **Webhook URL**: `https://your-backend.railway.app/webhook/n8n/video-upload`
2. **API Endpoints**: All existing endpoints work
3. **Authentication**: API key in query params or headers

## 🧪 Testing the Setup

### **Test Frontend:**
```bash
# Visit your Netlify site
https://your-site.netlify.app
```

### **Test Backend:**
```bash
# Test API health
curl https://your-backend.railway.app/api/health

# Test with API key
curl "https://your-backend.railway.app/n8n/test-connection?api_key=YOUR_KEY"
```

### **Test Integration:**
```bash
# Test from frontend to backend
# Use browser dev tools to check API calls
```

## 💰 Cost Estimation

### **Netlify (Frontend):**
- ✅ **Free tier**: 100GB bandwidth, 300 build minutes
- 💰 **Pro**: $19/month for more features

### **Railway (Backend):**
- ✅ **Free tier**: $5 credit monthly
- 💰 **Usage-based**: ~$5-20/month for small apps

### **Total Monthly Cost:**
- 🆓 **Free tier**: $0 (with limitations)
- 💰 **Production**: $5-39/month

## ⚠️ Important Considerations

### **CORS Configuration:**
Your backend must allow requests from your Netlify domain:
```python
# In app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-site.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### **API Security:**
- Use HTTPS only
- Implement rate limiting
- Validate API keys
- Log security events

### **Database Considerations:**
- SQLite won't work on Railway (use PostgreSQL)
- Backup strategy needed
- Migration scripts required

## 🎯 Next Steps

1. **Choose Backend Hosting** (Railway recommended)
2. **Reorganize Repository** (frontend/backend split)
3. **Deploy Backend** with environment variables
4. **Update Frontend** to use backend API
5. **Test Integration** end-to-end
6. **Configure Domain** (optional)

This hybrid approach gives you the best of both worlds: fast static site delivery via Netlify CDN and powerful backend functionality via dedicated hosting.
