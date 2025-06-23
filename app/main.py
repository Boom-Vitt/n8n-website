from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime, timedelta, timezone
import json
import httpx

from .database import Base, engine, get_db
from .models import User, Post, ScheduledPost, APIKeyUsage
from .auth import verify_token, create_access_token, get_current_user, get_user_from_api_key, SSOHandler, create_or_get_sso_user, log_api_usage, get_api_key_stats, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from .social_media import SocialMediaManager
from .scheduler import schedule_post
from .middleware import RateLimitMiddleware, APIKeyValidationMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Social Media Management API", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS middleware - configured for Netlify deployment
allowed_origins = [
    "http://localhost:3000",  # Local development
    "http://localhost:8000",  # Local development
    "https://*.netlify.app",  # Netlify preview deployments
    "https://boombignose.netlify.app",  # Your Netlify domain (update this)
    "https://boombignose.com",  # Your custom domain (if any)
]

# Get additional origins from environment
env_origins = config("CORS_ORIGINS", default="").split(",")
if env_origins and env_origins[0]:
    allowed_origins.extend([origin.strip() for origin in env_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add rate limiting and API key validation
app.add_middleware(RateLimitMiddleware, calls=1000, period=3600)  # 1000 calls per hour
app.add_middleware(APIKeyValidationMiddleware)

security = HTTPBearer()
social_manager = SocialMediaManager()

class PostCreate(BaseModel):
    content: str
    platforms: List[str]
    media_urls: Optional[List[str]] = None
    scheduled_time: Optional[datetime] = None

class PostResponse(BaseModel):
    id: int
    content: str
    platforms: List[str]
    status: str
    created_at: datetime
    scheduled_time: Optional[datetime] = None

class VideoPostCreate(BaseModel):
    content: str
    platforms: List[str]
    video_url: str
    video_title: Optional[str] = None
    video_description: Optional[str] = None
    video_tags: Optional[List[str]] = None
    scheduled_time: Optional[datetime] = None

class SSOLogin(BaseModel):
    token: str
    provider: str  # google only

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    api_key: Optional[str] = None
    created_at: datetime

class APIKeyRequest(BaseModel):
    name: str = "Default API Key"

class APIKeyResponse(BaseModel):
    api_key: str
    name: str
    created_at: datetime
    is_active: bool
    usage_count: int
    last_used: Optional[datetime] = None

class APIKeyStats(BaseModel):
    api_key_active: bool
    api_key_created: Optional[datetime]
    api_key_name: Optional[str]
    total_usage: int
    last_used: Optional[datetime]
    recent_usage_30_days: int
    success_rate: float
    popular_endpoints: List[dict]

class PlatformConnection(BaseModel):
    platform: str  # facebook, instagram, tiktok, youtube
    access_token: str
    page_id: Optional[str] = None  # for facebook
    account_id: Optional[str] = None  # for instagram
    user_id: Optional[str] = None  # for tiktok
    channel_id: Optional[str] = None  # for youtube

class ConnectedPlatforms(BaseModel):
    facebook: bool = False
    instagram: bool = False
    tiktok: bool = False
    youtube: bool = False

class N8NConnectionGuide(BaseModel):
    api_key: str
    base_url: str
    endpoints: dict
    example_requests: dict

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/health")
async def api_health():
    return {"message": "Social Media Management API", "version": "1.0.0", "status": "healthy"}

# Traditional login removed - Google SSO only

@app.post("/posts/", response_model=PostResponse)
async def create_post(
    post: PostCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    user = verify_token(credentials.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    new_post = ScheduledPost(
        user_id=user.id,
        content=post.content,
        platforms=json.dumps(post.platforms),
        media_urls=json.dumps(post.media_urls) if post.media_urls else None,
        scheduled_time=post.scheduled_time,
        status="pending_approval"
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    if post.scheduled_time:
        schedule_post.delay(new_post.id)
    
    return PostResponse(
        id=new_post.id,
        content=new_post.content,
        platforms=json.loads(new_post.platforms),
        status=new_post.status,
        created_at=new_post.created_at,
        scheduled_time=new_post.scheduled_time
    )

@app.get("/posts/", response_model=List[PostResponse])
async def get_posts(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    user = verify_token(credentials.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    posts = db.query(ScheduledPost).filter(ScheduledPost.user_id == user.id).all()
    
    return [
        PostResponse(
            id=post.id,
            content=post.content,
            platforms=json.loads(post.platforms),
            status=post.status,
            created_at=post.created_at,
            scheduled_time=post.scheduled_time
        )
        for post in posts
    ]

@app.post("/posts/{post_id}/approve")
async def approve_post(
    post_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    user = verify_token(credentials.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    post = db.query(ScheduledPost).filter(
        ScheduledPost.id == post_id,
        ScheduledPost.user_id == user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Post already processed")
    
    post.status = "approved"
    db.commit()
    
    if post.scheduled_time and post.scheduled_time <= datetime.utcnow():
        result = await social_manager.publish_post(
            content=post.content,
            platforms=json.loads(post.platforms),
            media_urls=json.loads(post.media_urls) if post.media_urls else None
        )
        
        post.status = "published" if result.get("success") else "failed"
        post.published_at = datetime.utcnow()
        db.commit()
    
    return {"message": "Post approved successfully"}

@app.get("/platforms/")
async def get_supported_platforms():
    return {
        "platforms": [
            {"name": "facebook", "display_name": "Facebook"},
            {"name": "instagram", "display_name": "Instagram"},
            {"name": "tiktok", "display_name": "TikTok"},
            {"name": "youtube", "display_name": "YouTube"}
        ]
    }

# Google SSO Authentication (only supported provider)
@app.post("/auth/sso", response_model=dict)
async def sso_login(sso_data: SSOLogin, db = Depends(get_db)):
    if sso_data.provider != "google":
        raise HTTPException(status_code=400, detail="Only Google SSO is supported")
    
    sso_handler = SSOHandler()
    user_info = await sso_handler.verify_google_token(sso_data.token)
    
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    # Create or get user
    user = create_or_get_sso_user(user_info, db)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "connected_platforms": {
                "facebook": user.facebook_connected,
                "instagram": user.instagram_connected,
                "tiktok": user.tiktok_connected,
                "youtube": user.youtube_connected
            }
        }
    }

# Social Media Platform Connection Endpoints
@app.post("/auth/connect-platform")
async def connect_social_platform(
    platform_data: PlatformConnection,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    platform = platform_data.platform.lower()
    
    if platform == "facebook":
        current_user.connect_facebook(platform_data.access_token, platform_data.page_id)
    elif platform == "instagram":
        current_user.connect_instagram(platform_data.access_token, platform_data.account_id)
    elif platform == "tiktok":
        current_user.connect_tiktok(platform_data.access_token, platform_data.user_id)
    elif platform == "youtube":
        current_user.connect_youtube(platform_data.access_token, platform_data.channel_id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    db.commit()
    
    return {
        "message": f"{platform.title()} connected successfully",
        "platform": platform,
        "connected": True
    }

@app.post("/auth/disconnect-platform")
async def disconnect_social_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    platform = platform.lower()
    supported_platforms = ["facebook", "instagram", "tiktok", "youtube"]
    
    if platform not in supported_platforms:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    current_user.disconnect_platform(platform)
    db.commit()
    
    return {
        "message": f"{platform.title()} disconnected successfully",
        "platform": platform,
        "connected": False
    }

@app.get("/auth/connected-platforms", response_model=ConnectedPlatforms)
async def get_connected_platforms(
    current_user: User = Depends(get_current_user)
):
    return ConnectedPlatforms(
        facebook=current_user.facebook_connected,
        instagram=current_user.instagram_connected,
        tiktok=current_user.tiktok_connected,
        youtube=current_user.youtube_connected
    )

# OAuth URL Generation Endpoints
@app.get("/auth/oauth-url/{platform}")
async def get_oauth_url(
    platform: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/callback/{platform}"
    
    sso_handler = SSOHandler()
    
    if platform == "facebook":
        oauth_url = f"https://www.facebook.com/v18.0/dialog/oauth?client_id={FACEBOOK_APP_ID}&redirect_uri={redirect_uri}&scope=pages_manage_posts,pages_read_engagement,pages_show_list&response_type=code&state={current_user.id}"
    elif platform == "instagram":
        oauth_url = f"https://api.instagram.com/oauth/authorize?client_id={INSTAGRAM_APP_ID}&redirect_uri={redirect_uri}&scope=user_profile,user_media&response_type=code&state={current_user.id}"
    elif platform == "tiktok":
        # TikTok requires manual approval for Content Posting API
        if not TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_KEY == "your-tiktok-client-key":
            raise HTTPException(status_code=400, detail="TikTok API not configured. Content Posting API requires manual approval from TikTok.")
        oauth_url = f"https://www.tiktok.com/auth/authorize/?client_key={TIKTOK_CLIENT_KEY}&scope=user.info.basic,video.upload&response_type=code&redirect_uri={redirect_uri}&state={current_user.id}"
    elif platform == "youtube":
        # YouTube uses Google OAuth with same credentials
        if not YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_ID == "your-youtube-client-id":
            raise HTTPException(status_code=400, detail="YouTube API not configured. Please enable YouTube Data API v3 in Google Cloud Console and update OAuth scopes.")
        # Try port 8000 which might already be registered
        youtube_redirect_uri = "http://localhost:8000/auth/google/callback"
        print(f"YouTube OAuth URL redirect_uri: {youtube_redirect_uri}")
        oauth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={YOUTUBE_CLIENT_ID}&redirect_uri={youtube_redirect_uri}&scope=https://www.googleapis.com/auth/youtube.upload&response_type=code&access_type=offline&state=youtube_{current_user.id}"
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    return {
        "oauth_url": oauth_url,
        "platform": platform,
        "redirect_uri": redirect_uri
    }

# OAuth Token Exchange Functions
async def exchange_tiktok_code(code: str, redirect_uri: str) -> str:
    """Exchange TikTok authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://open-api.tiktok.com/oauth/access_token/",
            data={
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
        )
        result = response.json()
        if result.get("data", {}).get("access_token"):
            return result["data"]["access_token"]
        raise Exception(f"TikTok token exchange failed: {result}")

async def get_tiktok_user_info(access_token: str) -> dict:
    """Get TikTok user information"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://open-api.tiktok.com/user/info/",
            json={
                "access_token": access_token,
                "fields": ["open_id", "union_id", "avatar_url", "display_name"]
            }
        )
        result = response.json()
        if result.get("data", {}).get("user"):
            return result["data"]["user"]
        raise Exception(f"TikTok user info failed: {result}")

async def exchange_youtube_code(code: str, redirect_uri: str) -> str:
    """Exchange YouTube authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": YOUTUBE_CLIENT_ID,
                "client_secret": YOUTUBE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
        )
        result = response.json()
        if result.get("access_token"):
            return result["access_token"]
        raise Exception(f"YouTube token exchange failed: {result}")

async def get_youtube_channel_info(access_token: str) -> dict:
    """Get YouTube channel information"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "part": "id,snippet",
                "mine": "true",
                "access_token": access_token
            }
        )
        result = response.json()
        if result.get("items"):
            return result["items"][0]
        raise Exception(f"YouTube channel info failed: {result}")

async def exchange_facebook_code(code: str, redirect_uri: str) -> str:
    """Exchange Facebook authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        result = response.json()
        if result.get("access_token"):
            return result["access_token"]
        raise Exception(f"Facebook token exchange failed: {result}")

async def get_facebook_pages(access_token: str) -> list:
    """Get Facebook pages managed by user"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={
                "access_token": access_token,
                "fields": "id,name,access_token"
            }
        )
        result = response.json()
        if result.get("data"):
            return result["data"]
        raise Exception(f"Facebook pages failed: {result}")

async def exchange_instagram_code(code: str, redirect_uri: str) -> str:
    """Exchange Instagram authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": INSTAGRAM_APP_ID,
                "client_secret": INSTAGRAM_APP_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
        )
        result = response.json()
        if result.get("access_token"):
            return result["access_token"]
        raise Exception(f"Instagram token exchange failed: {result}")

async def get_instagram_account_info(access_token: str) -> dict:
    """Get Instagram account information"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.instagram.com/me",
            params={
                "fields": "id,username,account_type",
                "access_token": access_token
            }
        )
        result = response.json()
        if result.get("id"):
            return result
        raise Exception(f"Instagram account info failed: {result}")

# OAuth Callback Handlers for Platform Connections (requires state)
@app.get("/auth/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str,
    state: str,
    request: Request,
    db = Depends(get_db)
):
    # Verify state parameter (user ID)
    try:
        user_id = int(state)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/callback/{platform}"
    
    try:
        if platform == "tiktok":
            # Exchange code for TikTok access token
            access_token = await exchange_tiktok_code(code, redirect_uri)
            user_info = await get_tiktok_user_info(access_token)
            user.connect_tiktok(access_token, user_info.get("open_id"))
            
        elif platform == "youtube":
            # Exchange code for YouTube access token
            access_token = await exchange_youtube_code(code, redirect_uri)
            channel_info = await get_youtube_channel_info(access_token)
            user.connect_youtube(access_token, channel_info.get("id"))
            
        elif platform == "facebook":
            # Exchange code for Facebook access token
            access_token = await exchange_facebook_code(code, redirect_uri)
            pages = await get_facebook_pages(access_token)
            # For now, connect to first page (you might want to let user choose)
            if pages:
                user.connect_facebook(access_token, pages[0].get("id"))
            
        elif platform == "instagram":
            # Exchange code for Instagram access token
            access_token = await exchange_instagram_code(code, redirect_uri)
            account_info = await get_instagram_account_info(access_token)
            user.connect_instagram(access_token, account_info.get("id"))
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")
        
        db.commit()
        
        # Redirect to dashboard with success message
        return templates.TemplateResponse("connection_success.html", {
            "request": request,
            "platform": platform.title(),
            "success": True
        })
        
    except Exception as e:
        # Redirect to dashboard with error message
        return templates.TemplateResponse("connection_success.html", {
            "request": request,
            "platform": platform.title(),
            "success": False,
            "error": str(e)
        })

# Google OAuth callback for user authentication (different from platform connections)
@app.get("/auth/google/callback")
async def google_auth_callback(
    code: str,
    request: Request,
    db = Depends(get_db),
    scope: str = None,
    authuser: str = None,
    prompt: str = None,
    platform: str = None,
    state: str = None
):
    print(f"Google OAuth callback received - code: {code[:20]}...")
    print(f"Full request URL: {request.url}")
    print(f"Platform parameter: {platform}")
    print(f"State parameter: {state}")
    
    # Check if this is a YouTube platform connection by state prefix
    if state and state.startswith("youtube_"):
        # This is a YouTube platform connection
        try:
            user_id = int(state.replace("youtube_", ""))
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=400, detail="Invalid user")
            
            # Exchange code for YouTube access token  
            redirect_uri = f"{str(request.base_url).rstrip('/')}/auth/google/callback"
            print(f"YouTube token exchange with redirect_uri: {redirect_uri}")
            access_token = await exchange_youtube_code(code, redirect_uri)
            channel_info = await get_youtube_channel_info(access_token)
            user.connect_youtube(access_token, channel_info.get("id"))
            
            db.commit()
            
            return templates.TemplateResponse("connection_success.html", {
                "request": request,
                "platform": "YouTube",
                "success": True
            })
            
        except Exception as e:
            return templates.TemplateResponse("connection_success.html", {
                "request": request,
                "platform": "YouTube",
                "success": False,
                "error": str(e)
            })
    
    # Regular user authentication flow
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"{str(request.base_url).rstrip('/')}/auth/google/callback"
                }
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.text
                print(f"Token exchange failed: {error_detail}")
                raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {error_detail}")
            
            token_data = token_response.json()
            print(f"Token response: {token_data}")
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")
            
            # Get user info from Google
            user_response = await client.get(
                f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}"
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            user_info = user_response.json()
            
            # Create or get user
            user = create_or_get_sso_user({
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "provider": "google"
            }, db)
            
            # Create JWT token
            jwt_token = create_access_token(data={"sub": user.username})
            
            # Return success page with auto-redirect
            return templates.TemplateResponse("google_auth_success.html", {
                "request": request,
                "access_token": jwt_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            })
            
    except Exception as e:
        print(f"Google OAuth error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        return templates.TemplateResponse("google_auth_error.html", {
            "request": request,
            "error": str(e)
        })

# API Key Management
@app.post("/auth/generate-api-key", response_model=APIKeyResponse)
async def generate_api_key(
    key_request: APIKeyRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    api_key = current_user.generate_api_key(key_request.name)
    db.commit()
    db.refresh(current_user)
    
    return APIKeyResponse(
        api_key=api_key,
        name=current_user.api_key_name,
        created_at=current_user.api_key_created_at,
        is_active=current_user.api_key_is_active,
        usage_count=current_user.api_key_usage_count or 0,
        last_used=current_user.api_key_last_used
    )

@app.post("/auth/revoke-api-key")
async def revoke_api_key(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    if not current_user.api_key:
        raise HTTPException(status_code=404, detail="No API key found")
    
    current_user.revoke_api_key()
    db.commit()
    return {"message": "API key revoked successfully"}

@app.get("/auth/api-key-stats", response_model=APIKeyStats)
async def get_api_key_statistics(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    stats = get_api_key_stats(current_user.id, db)
    return APIKeyStats(**stats)

@app.get("/auth/api-key-status")
async def get_api_key_status(
    current_user: User = Depends(get_current_user)
):
    return {
        "has_api_key": bool(current_user.api_key),
        "api_key_active": current_user.api_key_is_active if current_user.api_key else False,
        "api_key_name": current_user.api_key_name,
        "created_at": current_user.api_key_created_at,
        "usage_count": current_user.api_key_usage_count or 0,
        "last_used": current_user.api_key_last_used
    }

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        api_key=current_user.api_key,
        created_at=current_user.created_at
    )

# n8n Integration Endpoints
@app.post("/api/posts/video", response_model=PostResponse)
async def create_video_post_via_api(
    post: VideoPostCreate,
    api_key: str,
    db = Depends(get_db)
):
    user = await get_user_from_api_key(api_key, db)
    
    # Log API usage
    log_api_usage(
        user.id,
        "/api/posts/video",
        "POST",
        True,
        db=db
    )
    
    new_post = ScheduledPost(
        user_id=user.id,
        content=post.content,
        platforms=json.dumps(post.platforms),
        video_url=post.video_url,
        video_title=post.video_title,
        video_description=post.video_description,
        video_tags=json.dumps(post.video_tags) if post.video_tags else None,
        scheduled_time=post.scheduled_time,
        status="pending_approval"
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    if post.scheduled_time:
        schedule_post.delay(new_post.id)
    
    return PostResponse(
        id=new_post.id,
        content=new_post.content,
        platforms=json.loads(new_post.platforms),
        status=new_post.status,
        created_at=new_post.created_at,
        scheduled_time=new_post.scheduled_time
    )

@app.post("/api/posts/video/{post_id}/approve")
async def approve_video_post_via_api(
    post_id: int,
    api_key: str,
    db = Depends(get_db)
):
    user = await get_user_from_api_key(api_key, db)
    
    # Log API usage
    log_api_usage(
        user.id,
        f"/api/posts/video/{post_id}/approve",
        "POST",
        True,
        db=db
    )
    
    post = db.query(ScheduledPost).filter(
        ScheduledPost.id == post_id,
        ScheduledPost.user_id == user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Post already processed")
    
    post.status = "approved"
    db.commit()
    
    # Auto-publish if scheduled time has passed
    if post.scheduled_time and post.scheduled_time <= datetime.utcnow():
        result = await social_manager.publish_video_post(
            content=post.content,
            platforms=json.loads(post.platforms),
            video_url=post.video_url,
            video_title=post.video_title,
            video_description=post.video_description,
            video_tags=json.loads(post.video_tags) if post.video_tags else None
        )
        
        post.status = "published" if result.get("success") else "failed"
        post.published_at = datetime.utcnow()
        db.commit()
    
    return {"message": "Video post approved successfully"}

# n8n Webhook Endpoints
@app.post("/webhook/n8n/video-upload")
async def n8n_video_upload_webhook(
    api_key: str,
    video_data: dict,
    db = Depends(get_db)
):
    user = await get_user_from_api_key(api_key, db)
    
    # Create video post from n8n webhook data
    new_post = ScheduledPost(
        user_id=user.id,
        content=video_data.get("content", ""),
        platforms=json.dumps(video_data.get("platforms", ["facebook", "instagram", "tiktok"])),
        video_url=video_data.get("video_url"),
        video_title=video_data.get("title"),
        video_description=video_data.get("description"),
        video_tags=json.dumps(video_data.get("tags", [])),
        status="approved" if video_data.get("auto_approve", False) else "pending_approval"
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # Auto-publish if approved
    if new_post.status == "approved":
        result = await social_manager.publish_video_post(
            content=new_post.content,
            platforms=json.loads(new_post.platforms),
            video_url=new_post.video_url,
            video_title=new_post.video_title,
            video_description=new_post.video_description,
            video_tags=json.loads(new_post.video_tags) if new_post.video_tags else None
        )
        
        new_post.status = "published" if result.get("success") else "failed"
        new_post.published_at = datetime.utcnow()
        db.commit()
    
    # Log API usage
    log_api_usage(
        user.id, 
        "/webhook/n8n/video-upload", 
        "POST", 
        True, 
        db=db
    )
    
    return {
        "message": "Video post created successfully",
        "post_id": new_post.id,
        "status": new_post.status
    }

# n8n Connection Guide and Documentation
@app.get("/n8n/connection-guide", response_model=N8NConnectionGuide)
async def get_n8n_connection_guide(
    request,
    current_user: User = Depends(get_current_user)
):
    base_url = str(request.base_url).rstrip('/')
    
    if not current_user.api_key:
        raise HTTPException(
            status_code=400, 
            detail="Please generate an API key first using POST /auth/generate-api-key"
        )
    
    return N8NConnectionGuide(
        api_key=current_user.api_key,
        base_url=base_url,
        endpoints={
            "create_video_post": f"{base_url}/api/posts/video",
            "approve_post": f"{base_url}/api/posts/video/{{post_id}}/approve",
            "webhook_upload": f"{base_url}/webhook/n8n/video-upload",
            "get_platforms": f"{base_url}/platforms/"
        },
        example_requests={
            "create_video_post": {
                "method": "POST",
                "url": f"{base_url}/api/posts/video?api_key={current_user.api_key}",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "content": "Check out this awesome video!",
                    "platforms": ["facebook", "instagram", "tiktok"],
                    "video_url": "https://example.com/video.mp4",
                    "video_title": "My Video Title",
                    "video_description": "Video description here",
                    "video_tags": ["video", "content", "social"]
                }
            },
            "webhook_upload": {
                "method": "POST",
                "url": f"{base_url}/webhook/n8n/video-upload?api_key={current_user.api_key}",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "content": "Auto-posted from n8n!",
                    "platforms": ["facebook", "instagram"],
                    "video_url": "https://example.com/video.mp4",
                    "title": "Auto Video",
                    "description": "Automatically posted video",
                    "tags": ["automation", "n8n"],
                    "auto_approve": True
                }
            }
        }
    )

@app.get("/n8n/test-connection")
async def test_n8n_connection(
    api_key: str,
    db = Depends(get_db)
):
    user = await get_user_from_api_key(api_key, db)
    
    # Log test connection
    log_api_usage(
        user.id,
        "/n8n/test-connection",
        "GET",
        True,
        db=db
    )
    
    return {
        "status": "success",
        "message": "API key is valid and working",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Dashboard endpoints for API key management
@app.get("/dashboard/api-usage")
async def get_dashboard_api_usage(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    from sqlalchemy import func
    from .models import APIKeyUsage
    from datetime import timedelta
    
    # Get usage data for the last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    daily_usage = db.query(
        func.date(APIKeyUsage.timestamp).label('date'),
        func.count(APIKeyUsage.id).label('count')
    ).filter(
        APIKeyUsage.user_id == current_user.id,
        APIKeyUsage.timestamp >= seven_days_ago
    ).group_by(func.date(APIKeyUsage.timestamp)).all()
    
    return {
        "api_key_info": {
            "name": current_user.api_key_name,
            "created_at": current_user.api_key_created_at,
            "is_active": current_user.api_key_is_active,
            "total_usage": current_user.api_key_usage_count or 0,
            "last_used": current_user.api_key_last_used
        },
        "daily_usage": [{
            "date": str(date),
            "count": count
        } for date, count in daily_usage]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)