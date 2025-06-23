from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
from .database import Base
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Google SSO for authentication (required)
    google_id = Column(String(100), unique=True, nullable=False)
    
    # Social media platform tokens for posting
    facebook_access_token = Column(Text, nullable=True)
    facebook_page_id = Column(String(100), nullable=True)
    instagram_access_token = Column(Text, nullable=True)
    instagram_account_id = Column(String(100), nullable=True)
    tiktok_access_token = Column(Text, nullable=True)
    tiktok_user_id = Column(String(100), nullable=True)
    youtube_access_token = Column(Text, nullable=True)
    youtube_channel_id = Column(String(100), nullable=True)
    
    # Platform connection status
    facebook_connected = Column(Boolean, default=False)
    instagram_connected = Column(Boolean, default=False)
    tiktok_connected = Column(Boolean, default=False)
    youtube_connected = Column(Boolean, default=False)
    
    # API Key for n8n integration
    api_key = Column(String(64), unique=True, nullable=True)
    api_key_created_at = Column(DateTime(timezone=True), nullable=True)
    api_key_name = Column(String(100), nullable=True)
    api_key_last_used = Column(DateTime(timezone=True), nullable=True)
    api_key_usage_count = Column(Integer, default=0)
    api_key_is_active = Column(Boolean, default=True)
    
    posts = relationship("Post", back_populates="user")
    scheduled_posts = relationship("ScheduledPost", back_populates="user")
    
    def connect_facebook(self, access_token: str, page_id: str = None):
        self.facebook_access_token = access_token
        self.facebook_page_id = page_id
        self.facebook_connected = True
    
    def connect_instagram(self, access_token: str, account_id: str = None):
        self.instagram_access_token = access_token
        self.instagram_account_id = account_id
        self.instagram_connected = True
    
    def connect_tiktok(self, access_token: str, user_id: str = None):
        self.tiktok_access_token = access_token
        self.tiktok_user_id = user_id
        self.tiktok_connected = True
    
    def connect_youtube(self, access_token: str, channel_id: str = None):
        self.youtube_access_token = access_token
        self.youtube_channel_id = channel_id
        self.youtube_connected = True
    
    def disconnect_platform(self, platform: str):
        if platform == "facebook":
            self.facebook_access_token = None
            self.facebook_page_id = None
            self.facebook_connected = False
        elif platform == "instagram":
            self.instagram_access_token = None
            self.instagram_account_id = None
            self.instagram_connected = False
        elif platform == "tiktok":
            self.tiktok_access_token = None
            self.tiktok_user_id = None
            self.tiktok_connected = False
        elif platform == "youtube":
            self.youtube_access_token = None
            self.youtube_channel_id = None
            self.youtube_connected = False
    
    def generate_api_key(self, name: str = "Default API Key") -> str:
        self.api_key = secrets.token_urlsafe(48)
        self.api_key_created_at = func.now()
        self.api_key_name = name
        self.api_key_is_active = True
        self.api_key_usage_count = 0
        return self.api_key
    
    def revoke_api_key(self):
        self.api_key_is_active = False
    
    def update_api_key_usage(self):
        self.api_key_last_used = func.now()
        self.api_key_usage_count = (self.api_key_usage_count or 0) + 1

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    platforms = Column(Text, nullable=False)  # JSON string
    media_urls = Column(Text, nullable=True)  # JSON string
    status = Column(String(20), default="draft")  # draft, published, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="posts")

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    platforms = Column(Text, nullable=False)  # JSON string
    media_urls = Column(Text, nullable=True)  # JSON string
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending_approval")  # pending_approval, approved, published, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Video-specific fields for n8n integration
    video_url = Column(String(500), nullable=True)
    video_title = Column(String(200), nullable=True)
    video_description = Column(Text, nullable=True)
    video_tags = Column(Text, nullable=True)  # JSON string
    
    user = relationship("User", back_populates="scheduled_posts")

class APIKeyUsage(Base):
    __tablename__ = "api_key_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    user = relationship("User")