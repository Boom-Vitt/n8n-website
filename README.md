# Social Media Management API

A complete FastAPI-based social media management system with SSO authentication, API key management, and n8n integration for video posting across Facebook, Instagram, and TikTok.

## Features

- **SSO Authentication**: Google, Facebook, and GitHub OAuth integration
- **API Key Management**: Generate API keys for external integrations
- **Multi-Platform Posting**: Support for Facebook, Instagram, and TikTok
- **Video Support**: Specialized endpoints for video content
- **n8n Integration**: Webhook endpoints for n8n automation
- **Scheduled Posting**: Celery-based background task processing
- **Approval Workflow**: Posts require approval before publishing

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start Redis (for Celery)**
   ```bash
   redis-server
   ```

4. **Start Celery Worker**
   ```bash
   celery -A app.scheduler.celery_app worker --loglevel=info
   ```

5. **Start Celery Beat (for scheduled tasks)**
   ```bash
   celery -A app.scheduler.celery_app beat --loglevel=info
   ```

6. **Run the Application**
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Endpoints

### Authentication

- `POST /auth/login` - Standard username/password login
- `POST /auth/sso` - SSO login (Google, Facebook, GitHub)
- `POST /auth/generate-api-key` - Generate API key for current user
- `GET /auth/me` - Get current user information

### Posts Management

- `POST /posts/` - Create a new post
- `GET /posts/` - Get user's posts
- `POST /posts/{post_id}/approve` - Approve a post for publishing

### n8n Integration

- `POST /api/posts/video` - Create video post via API key
- `POST /api/posts/video/{post_id}/approve` - Approve video post via API key
- `POST /webhook/n8n/video-upload` - n8n webhook for video uploads

### Platform Support

- `GET /platforms/` - Get supported social media platforms

## n8n Integration Guide

1. **Get API Key**
   - Login to the application
   - Call `POST /auth/generate-api-key` to get your API key

2. **Create Video Post from n8n**
   ```bash
   curl -X POST "http://localhost:8000/api/posts/video" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "Check out this awesome video!",
       "platforms": ["facebook", "instagram", "tiktok"],
       "video_url": "https://example.com/video.mp4",
       "video_title": "My Video Title",
       "video_description": "Video description here",
       "video_tags": ["video", "content", "social"]
     }' \
     -G -d "api_key=YOUR_API_KEY"
   ```

3. **n8n Webhook Integration**
   ```bash
   curl -X POST "http://localhost:8000/webhook/n8n/video-upload" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "Auto-posted from n8n!",
       "platforms": ["facebook", "instagram"],
       "video_url": "https://example.com/video.mp4",
       "title": "Auto Video",
       "description": "Automatically posted video",
       "tags": ["automation", "n8n"],
       "auto_approve": true
     }' \
     -G -d "api_key=YOUR_API_KEY"
   ```

## Environment Variables

See `.env.example` for all required environment variables including:

- Database configuration
- JWT secret key
- Social media platform API keys
- SSO provider credentials
- Celery/Redis configuration

## Architecture

- **FastAPI**: Web framework and API server
- **SQLAlchemy**: Database ORM
- **Celery + Redis**: Background task processing
- **JWT**: Authentication tokens
- **OAuth**: SSO integration
- **httpx**: HTTP client for social media APIs

## Security Features

- JWT-based authentication
- API key management for external integrations
- SSO with major providers
- Secure password hashing with bcrypt
- CORS middleware for cross-origin requests

## Development

Run tests:
```bash
pytest
```

The application follows a modular architecture with separate modules for:
- `database.py` - Database configuration
- `models.py` - SQLAlchemy models
- `auth.py` - Authentication and SSO
- `social_media.py` - Platform integrations
- `scheduler.py` - Background tasks
- `main.py` - FastAPI application and routes