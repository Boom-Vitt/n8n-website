# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m app.main
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests (if test files exist)
pytest

# Install additional development dependencies for testing
pip install pytest pytest-asyncio
```

## Architecture

This is a FastAPI-based social media management system that allows users to create, schedule, and manage posts across multiple social media platforms (Facebook, Instagram, TikTok).

### Core Structure

The application follows a modular architecture with the following key components:

- **app/main.py** - Main FastAPI application with API endpoints
- **Missing modules** that main.py imports (need to be created):
  - `database.py` - SQLAlchemy database setup, Base, engine, get_db
  - `models.py` - Database models (User, Post, ScheduledPost)
  - `auth.py` - Authentication logic (verify_token, create_access_token)  
  - `social_media.py` - Social media platform integrations (SocialMediaManager)
  - `scheduler.py` - Background task scheduling (schedule_post using Celery)

### Key Workflows

1. **Authentication Flow** - JWT-based authentication with Bearer tokens
2. **Post Creation** - Users create posts targeting multiple platforms with optional scheduling
3. **Approval Process** - Posts require approval before publication (status: pending_approval → approved)
4. **Publishing** - Approved posts are published immediately or scheduled via Celery tasks
5. **Multi-platform Support** - Single post can target Facebook, Instagram, and TikTok

### Database Models Structure

Based on the main.py usage:
- **User** - User accounts with username/password authentication
- **Post** - Basic post model
- **ScheduledPost** - Posts with scheduling capabilities, approval status, platform targeting

### Technology Stack

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM for database operations
- **Celery + Redis** - Background task processing
- **JWT** - Authentication tokens
- **Pydantic** - Data validation and serialization

### Status Flow

Posts follow this status progression:
`pending_approval` → `approved` → `published`/`failed`

The system supports both immediate and scheduled posting, with manual approval required before publication.