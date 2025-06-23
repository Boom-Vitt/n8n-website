"""
File Management Service for AI Video Uploader
Ensures privacy compliance with automatic file cleanup
"""

import os
import time
import tempfile
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FileManager:
    """
    Manages temporary file operations with privacy compliance
    - Automatic cleanup of temporary files
    - Secure file handling
    - Privacy policy compliance
    """
    
    def __init__(self, cleanup_hours: int = 24):
        self.cleanup_hours = cleanup_hours
        self.temp_dir = Path(tempfile.gettempdir()) / "ai_video_uploader"
        self.temp_dir.mkdir(exist_ok=True)
        
    async def create_temp_file(self, content: bytes, extension: str = ".mp4") -> str:
        """
        Create a temporary file with automatic cleanup scheduling
        
        Args:
            content: File content as bytes
            extension: File extension (default: .mp4)
            
        Returns:
            str: Path to temporary file
        """
        timestamp = int(time.time())
        filename = f"upload_{timestamp}_{os.urandom(8).hex()}{extension}"
        file_path = self.temp_dir / filename
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Schedule cleanup
        asyncio.create_task(self._schedule_cleanup(str(file_path)))
        
        logger.info(f"Created temporary file: {file_path}")
        return str(file_path)
    
    async def download_to_temp(self, url: str, extension: str = ".mp4") -> str:
        """
        Download file from URL to temporary location
        
        Args:
            url: URL to download from
            extension: File extension
            
        Returns:
            str: Path to downloaded temporary file
        """
        import httpx
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return await self.create_temp_file(response.content, extension)
    
    async def cleanup_file(self, file_path: str) -> bool:
        """
        Immediately cleanup a specific file
        
        Args:
            file_path: Path to file to cleanup
            
        Returns:
            bool: True if successfully cleaned up
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
            return False
    
    async def cleanup_old_files(self) -> int:
        """
        Cleanup all files older than cleanup_hours
        
        Returns:
            int: Number of files cleaned up
        """
        cleaned_count = 0
        cutoff_time = time.time() - (self.cleanup_hours * 3600)
        
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = file_path.stat().st_mtime
                    if file_age < cutoff_time:
                        if await self.cleanup_file(str(file_path)):
                            cleaned_count += 1
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old files")
        
        return cleaned_count
    
    async def _schedule_cleanup(self, file_path: str):
        """
        Schedule file cleanup after specified hours
        
        Args:
            file_path: Path to file to cleanup
        """
        # Wait for cleanup time
        await asyncio.sleep(self.cleanup_hours * 3600)
        await self.cleanup_file(file_path)
    
    async def get_temp_file_stats(self) -> dict:
        """
        Get statistics about temporary files
        
        Returns:
            dict: File statistics
        """
        try:
            files = list(self.temp_dir.iterdir())
            total_files = len([f for f in files if f.is_file()])
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "temp_directory": str(self.temp_dir),
                "cleanup_hours": self.cleanup_hours
            }
        except Exception as e:
            logger.error(f"Error getting file stats: {e}")
            return {"error": str(e)}

class PrivacyCompliantUploader:
    """
    Privacy-compliant file uploader for TikTok integration
    Ensures all uploads follow privacy policy requirements
    """
    
    def __init__(self):
        self.file_manager = FileManager()
        
    async def process_video_upload(
        self, 
        video_url: str, 
        callback_func,
        cleanup_immediately: bool = True
    ) -> dict:
        """
        Process video upload with privacy compliance
        
        Args:
            video_url: URL of video to upload
            callback_func: Function to call with temporary file path
            cleanup_immediately: Whether to cleanup immediately after processing
            
        Returns:
            dict: Upload result
        """
        temp_file_path = None
        
        try:
            # Step 1: Download to temporary location
            logger.info(f"Downloading video from: {video_url}")
            temp_file_path = await self.file_manager.download_to_temp(video_url)
            
            # Step 2: Process upload
            logger.info(f"Processing upload with temporary file: {temp_file_path}")
            result = await callback_func(temp_file_path)
            
            # Step 3: Immediate cleanup if requested
            if cleanup_immediately and temp_file_path:
                await self.file_manager.cleanup_file(temp_file_path)
                logger.info("Immediate cleanup completed")
            
            return {
                "success": True,
                "result": result,
                "privacy_compliance": {
                    "temporary_storage": True,
                    "auto_cleanup": True,
                    "data_minimization": True,
                    "immediate_deletion": cleanup_immediately
                }
            }
            
        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            
            # Ensure cleanup on error
            if temp_file_path:
                await self.file_manager.cleanup_file(temp_file_path)
            
            return {
                "success": False,
                "error": str(e),
                "privacy_compliance": {
                    "cleanup_on_error": True,
                    "no_data_retention": True
                }
            }

# Global instance for use across the application
file_manager = FileManager()
privacy_uploader = PrivacyCompliantUploader()

# Cleanup task for Celery
async def scheduled_cleanup_task():
    """Scheduled task to cleanup old temporary files"""
    return await file_manager.cleanup_old_files()
