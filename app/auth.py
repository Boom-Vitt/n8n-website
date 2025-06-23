from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from decouple import config
import httpx
import secrets

from .models import User, APIKeyUsage
from .database import get_db

SECRET_KEY = config('SECRET_KEY', default='your-secret-key-change-in-production-please')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Google SSO Configuration (for user authentication)
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

# Social Media Platform API Configuration (for posting)
FACEBOOK_APP_ID = config('FACEBOOK_APP_ID', default='')
FACEBOOK_APP_SECRET = config('FACEBOOK_APP_SECRET', default='')
INSTAGRAM_APP_ID = config('INSTAGRAM_APP_ID', default='')
INSTAGRAM_APP_SECRET = config('INSTAGRAM_APP_SECRET', default='')
TIKTOK_CLIENT_KEY = config('TIKTOK_CLIENT_KEY', default='')
TIKTOK_CLIENT_SECRET = config('TIKTOK_CLIENT_SECRET', default='')
YOUTUBE_CLIENT_ID = config('YOUTUBE_CLIENT_ID', default='')
YOUTUBE_CLIENT_SECRET = config('YOUTUBE_CLIENT_SECRET', default='')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, db: Session) -> Optional[User]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.username == username).first()
    return user

def verify_api_key(api_key: str, db: Session) -> Optional[User]:
    user = db.query(User).filter(
        User.api_key == api_key,
        User.api_key_is_active == True
    ).first()
    
    if user:
        # Update usage tracking
        user.update_api_key_usage()
        db.commit()
    
    return user

def log_api_usage(user_id: int, endpoint: str, method: str, success: bool, error_message: str = None, db: Session = None):
    """Log API key usage for analytics and monitoring"""
    if db:
        usage_log = APIKeyUsage(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            success=success,
            error_message=error_message
        )
        db.add(usage_log)
        db.commit()

def get_api_key_stats(user_id: int, db: Session) -> dict:
    """Get API key usage statistics for a user"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}
    
    # Last 30 days usage
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_usage = db.query(APIKeyUsage).filter(
        APIKeyUsage.user_id == user_id,
        APIKeyUsage.timestamp >= thirty_days_ago
    ).count()
    
    # Success rate
    total_calls = db.query(APIKeyUsage).filter(APIKeyUsage.user_id == user_id).count()
    successful_calls = db.query(APIKeyUsage).filter(
        APIKeyUsage.user_id == user_id,
        APIKeyUsage.success == True
    ).count()
    
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
    
    # Most used endpoints
    popular_endpoints = db.query(
        APIKeyUsage.endpoint,
        func.count(APIKeyUsage.endpoint).label('count')
    ).filter(
        APIKeyUsage.user_id == user_id
    ).group_by(APIKeyUsage.endpoint).order_by(desc('count')).limit(5).all()
    
    return {
        "api_key_active": user.api_key_is_active,
        "api_key_created": user.api_key_created_at,
        "api_key_name": user.api_key_name,
        "total_usage": user.api_key_usage_count or 0,
        "last_used": user.api_key_last_used,
        "recent_usage_30_days": recent_usage,
        "success_rate": round(success_rate, 2),
        "popular_endpoints": [{
            "endpoint": endpoint,
            "count": count
        } for endpoint, count in popular_endpoints]
    }

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    user = verify_token(credentials.credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_user_from_api_key(api_key: str, db: Session = Depends(get_db)) -> User:
    user = verify_api_key(api_key, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    return user

class SSOHandler:
    @staticmethod
    async def verify_google_token(token: str) -> Optional[dict]:
        """Verify Google ID token for user authentication"""
        async with httpx.AsyncClient() as client:
            try:
                # First try as ID token (JWT from Google Sign-In)
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
                )
                if response.status_code == 200:
                    token_info = response.json()
                    # Verify the token is for our app
                    if token_info.get("aud") == GOOGLE_CLIENT_ID:
                        return {
                            "id": token_info.get("sub"),
                            "email": token_info.get("email"),
                            "name": token_info.get("name"),
                            "provider": "google"
                        }
                
                # Fallback: try as access token
                response = await client.get(
                    f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={token}"
                )
                if response.status_code == 200:
                    user_info = response.json()
                    return {
                        "id": user_info.get("id"),
                        "email": user_info.get("email"),
                        "name": user_info.get("name"),
                        "provider": "google"
                    }
            except Exception as e:
                print(f"Google token verification error: {e}")
        return None
    
    @staticmethod
    async def get_facebook_oauth_url() -> str:
        """Get Facebook OAuth URL for connecting Facebook pages"""
        return f"https://www.facebook.com/v18.0/dialog/oauth?client_id={FACEBOOK_APP_ID}&redirect_uri=YOUR_REDIRECT_URI&scope=pages_manage_posts,pages_read_engagement,pages_show_list"
    
    @staticmethod
    async def get_instagram_oauth_url() -> str:
        """Get Instagram OAuth URL for connecting Instagram business accounts"""
        return f"https://api.instagram.com/oauth/authorize?client_id={INSTAGRAM_APP_ID}&redirect_uri=YOUR_REDIRECT_URI&scope=user_profile,user_media&response_type=code"
    
    @staticmethod
    async def get_tiktok_oauth_url() -> str:
        """Get TikTok OAuth URL for connecting TikTok accounts"""
        return f"https://www.tiktok.com/auth/authorize/?client_key={TIKTOK_CLIENT_KEY}&scope=user.info.basic,video.upload&response_type=code&redirect_uri=YOUR_REDIRECT_URI"
    
    @staticmethod
    async def get_youtube_oauth_url() -> str:
        """Get YouTube OAuth URL for connecting YouTube channels"""
        return f"https://accounts.google.com/o/oauth2/auth?client_id={YOUTUBE_CLIENT_ID}&redirect_uri=YOUR_REDIRECT_URI&scope=https://www.googleapis.com/auth/youtube.upload&response_type=code&access_type=offline"

def create_or_get_sso_user(sso_info: dict, db: Session) -> User:
    provider = sso_info["provider"]
    provider_id = sso_info["id"]
    email = sso_info["email"]
    name = sso_info["name"]
    
    # Only Google SSO is supported for authentication
    if provider != "google":
        raise ValueError("Only Google SSO is supported for authentication")
    
    # Check if user exists by Google ID
    user = db.query(User).filter(User.google_id == provider_id).first()
    
    if not user:
        # Check if user exists by email
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Link existing account to Google
            user.google_id = provider_id
        else:
            # Create new user with Google authentication
            username = email.split('@')[0] + '_' + secrets.token_hex(4)
            user = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),  # Random secure password
                google_id=provider_id
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)
    
    return user