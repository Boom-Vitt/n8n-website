# TikTok Content Posting API Integration Guide

## 🎯 Overview

This guide covers the complete integration of TikTok's Content Posting API with your AI Video Uploader system, ensuring compliance with privacy policies and TikTok's developer terms.

## 🔐 TikTok API Setup Requirements

### 1. TikTok Developer Account Setup
1. **Create TikTok Developer Account**: Visit [developers.tiktok.com](https://developers.tiktok.com/)
2. **Create New App**: Register your application
3. **Apply for Content Posting API**: This requires manual approval from TikTok
   - Provide detailed use case description
   - Explain your content moderation process
   - Show compliance with community guidelines

### 2. Required API Permissions
- `user.info.basic` - Basic user information
- `video.upload` - Video upload capability
- `video.publish` - Video publishing capability

### 3. Environment Configuration
Update your `.env` file with TikTok credentials:
```bash
TIKTOK_CLIENT_KEY=your-approved-client-key
TIKTOK_CLIENT_SECRET=your-client-secret
```

## 🔄 Integration Flow

### 1. User Authentication Flow
```
User → Google SSO Login → Dashboard → Connect TikTok → OAuth Flow → Store Tokens
```

### 2. Video Upload Flow
```
n8n/API → Video URL → Download Temp → Upload to TikTok → Create Draft → Cleanup
```

### 3. Privacy Compliance Flow
```
Upload → Private Draft Only → Manual Review → Optional Publish → Auto Cleanup
```

## 🛡️ Privacy & Security Implementation

### 1. File Handling (Compliant with Privacy Policy)
- ✅ **Temporary Storage**: Files stored in system temp directory
- ✅ **Auto Cleanup**: Files deleted within 24 hours or immediately after upload
- ✅ **Private Drafts**: All uploads create private drafts only
- ✅ **No Data Collection**: Only processes provided media and captions

### 2. Data Protection Measures
- ✅ **PDPA Compliant**: Follows Thailand Personal Data Protection Act
- ✅ **GDPR Principles**: Minimal data processing, purpose limitation
- ✅ **TikTok Terms**: Complies with TikTok Developer Terms of Service

## 🔧 Technical Implementation

### 1. Core Components Added
- **TikTok Video Upload**: `_publish_video_to_tiktok()` method
- **Temporary File Management**: Download, process, cleanup cycle
- **API Integration**: Official TikTok Content Posting API v2
- **Error Handling**: Comprehensive error management

### 2. API Endpoints Enhanced
- `POST /api/posts/video` - Enhanced with TikTok support
- `POST /webhook/n8n/video-upload` - n8n integration ready
- `GET /auth/oauth-url/tiktok` - TikTok OAuth URL generation

### 3. Database Schema
Already supports TikTok integration:
- `tiktok_access_token` - User's TikTok access token
- `tiktok_user_id` - TikTok user identifier
- `tiktok_connected` - Connection status

## 🚀 Deployment Checklist

### 1. Dependencies
```bash
pip install -r requirements.txt
# Includes: httpx, aiofiles, fastapi, celery, redis
```

### 2. Environment Setup
```bash
cp .env.example .env
# Configure TikTok API credentials
# Set up Redis for background tasks
```

### 3. Database Migration
```bash
python migrate_db.py
# Creates necessary tables if not exists
```

### 4. Start Services
```bash
# Start Redis
redis-server

# Start Celery Worker
celery -A app.scheduler.celery_app worker --loglevel=info

# Start API Server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 🧪 Testing the Integration

### 1. Test TikTok Connection
```bash
curl -X GET "http://localhost:8001/n8n/test-connection?api_key=YOUR_API_KEY"
```

### 2. Test Video Upload
```bash
curl -X POST "http://localhost:8001/api/posts/video?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test video from AI Video Uploader",
    "platforms": ["tiktok"],
    "video_url": "https://example.com/test-video.mp4",
    "video_title": "Test Upload",
    "video_description": "Testing TikTok integration"
  }'
```

### 3. Test n8n Webhook
```bash
curl -X POST "http://localhost:8001/webhook/n8n/video-upload?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Automated upload from n8n",
    "platforms": ["tiktok"],
    "video_url": "https://example.com/video.mp4",
    "auto_approve": false
  }'
```

## ⚠️ Important Limitations & Considerations

### 1. TikTok API Limitations
- **Manual Approval Required**: Content Posting API needs TikTok approval
- **Rate Limits**: Respect TikTok's API rate limits
- **Video Requirements**: MP4 format, max 10GB, specific dimensions
- **Draft Only**: System creates private drafts for manual review

### 2. Privacy Compliance
- **No Public Posting**: All uploads are private drafts
- **Temporary Storage**: Files auto-deleted after processing
- **Minimal Data**: Only processes provided content
- **User Control**: Manual approval required for all posts

### 3. Error Handling
- **Network Failures**: Retry logic with exponential backoff
- **File Cleanup**: Guaranteed cleanup even on failures
- **API Errors**: Detailed error reporting and logging

## 🔍 Monitoring & Analytics

### 1. API Usage Tracking
- Request counts and success rates
- Error logging and monitoring
- Performance metrics

### 2. File Management Monitoring
- Temporary file creation/deletion tracking
- Storage usage monitoring
- Cleanup verification

## 🆘 Troubleshooting

### Common Issues
1. **TikTok API Not Approved**: Apply for Content Posting API access
2. **File Upload Failures**: Check video format and size limits
3. **Token Expiration**: Implement token refresh mechanism
4. **Rate Limiting**: Implement proper backoff strategies

### Debug Mode
Set `DEBUG=True` in `.env` for detailed logging and error traces.

## 📞 Support & Resources

- **TikTok Developer Docs**: [developers.tiktok.com/doc](https://developers.tiktok.com/doc)
- **Content Posting API**: [TikTok Content Posting API Guide](https://developers.tiktok.com/doc/content-posting-api-get-started)
- **Community Guidelines**: [TikTok Community Guidelines](https://www.tiktok.com/community-guidelines)
