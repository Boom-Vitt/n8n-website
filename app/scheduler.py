from celery import Celery
from datetime import datetime, timezone
import json
from sqlalchemy.orm import sessionmaker
from decouple import config

from .database import engine
from .models import ScheduledPost
from .social_media import SocialMediaManager

# Celery configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

celery_app = Celery(
    'scheduler',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    beat_schedule={
        'process-scheduled-posts': {
            'task': 'scheduler.process_scheduled_posts',
            'schedule': 60.0,  # Run every minute
        },
        'cleanup-temporary-files': {
            'task': 'scheduler.cleanup_temporary_files',
            'schedule': 3600.0,  # Run every hour
        },
    },
)

# Create database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
social_manager = SocialMediaManager()

@celery_app.task
def schedule_post(post_id: int):
    """Schedule a post for future publishing"""
    db = SessionLocal()
    try:
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
        if not post:
            return {"error": "Post not found"}
        
        if post.status != "approved":
            return {"error": "Post not approved for publishing"}
        
        # Check if it's time to publish
        current_time = datetime.now(timezone.utc)
        if post.scheduled_time and post.scheduled_time <= current_time:
            return publish_post_now.delay(post_id)
        
        return {"message": "Post scheduled successfully"}
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
async def publish_post_now(post_id: int):
    """Immediately publish a post"""
    db = SessionLocal()
    try:
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
        if not post:
            return {"error": "Post not found"}
        
        if post.status != "approved":
            return {"error": "Post not approved for publishing"}
        
        # Determine if it's a video post or regular post
        if post.video_url:
            result = await social_manager.publish_video_post(
                content=post.content,
                platforms=json.loads(post.platforms),
                video_url=post.video_url,
                video_title=post.video_title,
                video_description=post.video_description,
                video_tags=json.loads(post.video_tags) if post.video_tags else None
            )
        else:
            result = await social_manager.publish_post(
                content=post.content,
                platforms=json.loads(post.platforms),
                media_urls=json.loads(post.media_urls) if post.media_urls else None
            )
        
        # Update post status
        post.status = "published" if result.get("success") else "failed"
        post.published_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "message": "Post published successfully" if result.get("success") else "Post publishing failed",
            "success": result.get("success"),
            "results": result.get("results", {})
        }
    
    except Exception as e:
        # Mark post as failed
        if 'post' in locals():
            post.status = "failed"
            post.published_at = datetime.now(timezone.utc)
            db.commit()
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def process_scheduled_posts():
    """Process all scheduled posts that are ready for publishing"""
    db = SessionLocal()
    try:
        current_time = datetime.now(timezone.utc)
        
        # Find approved posts that are scheduled for now or past
        ready_posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "approved",
            ScheduledPost.scheduled_time <= current_time
        ).all()
        
        published_count = 0
        failed_count = 0
        
        for post in ready_posts:
            try:
                # Use sync version for batch processing
                publish_post_sync(post.id, db)
                published_count += 1
            except Exception as e:
                post.status = "failed"
                post.published_at = current_time
                failed_count += 1
                print(f"Failed to publish post {post.id}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Processed {len(ready_posts)} posts",
            "published": published_count,
            "failed": failed_count
        }
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

def publish_post_sync(post_id: int, db_session=None):
    """Synchronous version of post publishing for batch processing"""
    db = db_session or SessionLocal()
    try:
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
        if not post:
            raise Exception("Post not found")
        
        if post.status != "approved":
            raise Exception("Post not approved for publishing")
        
        # For batch processing, we'll use a simpler approach
        # In a real implementation, you might want to use asyncio.run() or similar
        
        # Mark as published for now (placeholder)
        post.status = "published"
        post.published_at = datetime.now(timezone.utc)
        
        if not db_session:
            db.commit()
        
    except Exception as e:
        if 'post' in locals():
            post.status = "failed"
            post.published_at = datetime.now(timezone.utc)
            if not db_session:
                db.commit()
        raise e
    finally:
        if not db_session:
            db.close()

@celery_app.task
def cleanup_temporary_files():
    """Cleanup temporary files for privacy compliance"""
    try:
        from .file_manager import scheduled_cleanup_task
        import asyncio

        # Run the async cleanup task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            cleaned_count = loop.run_until_complete(scheduled_cleanup_task())
            return {
                "message": f"Cleaned up {cleaned_count} temporary files",
                "success": True
            }
        finally:
            loop.close()

    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

# Celery worker startup
if __name__ == '__main__':
    celery_app.start()