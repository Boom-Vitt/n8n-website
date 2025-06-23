import httpx
import json
import os
import time
import tempfile
from typing import List, Optional, Dict, Any
from decouple import config
import asyncio

class SocialMediaManager:
    def __init__(self):
        # Platform API credentials
        self.facebook_access_token = config('FACEBOOK_ACCESS_TOKEN', default='')
        self.facebook_page_id = config('FACEBOOK_PAGE_ID', default='')
        self.instagram_access_token = config('INSTAGRAM_ACCESS_TOKEN', default='')
        self.instagram_account_id = config('INSTAGRAM_ACCOUNT_ID', default='')
        self.tiktok_access_token = config('TIKTOK_ACCESS_TOKEN', default='')
        self.tiktok_account_id = config('TIKTOK_ACCOUNT_ID', default='')
    
    async def publish_post(
        self, 
        content: str, 
        platforms: List[str], 
        media_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        results = {}
        
        for platform in platforms:
            try:
                if platform == "facebook":
                    result = await self._publish_to_facebook(content, media_urls)
                elif platform == "instagram":
                    result = await self._publish_to_instagram(content, media_urls)
                elif platform == "tiktok":
                    result = await self._publish_to_tiktok(content, media_urls)
                else:
                    result = {"success": False, "error": f"Unsupported platform: {platform}"}
                
                results[platform] = result
            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}
        
        # Overall success if at least one platform succeeded
        overall_success = any(result.get("success", False) for result in results.values())
        
        return {
            "success": overall_success,
            "results": results
        }
    
    async def publish_video_post(
        self,
        content: str,
        platforms: List[str],
        video_url: str,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        video_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        results = {}
        
        for platform in platforms:
            try:
                if platform == "facebook":
                    result = await self._publish_video_to_facebook(
                        content, video_url, video_title, video_description
                    )
                elif platform == "instagram":
                    result = await self._publish_video_to_instagram(
                        content, video_url, video_title, video_description
                    )
                elif platform == "tiktok":
                    result = await self._publish_video_to_tiktok(
                        content, video_url, video_title, video_description, video_tags
                    )
                else:
                    result = {"success": False, "error": f"Unsupported platform: {platform}"}
                
                results[platform] = result
            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}
        
        overall_success = any(result.get("success", False) for result in results.values())
        
        return {
            "success": overall_success,
            "results": results
        }
    
    async def _publish_to_facebook(
        self, 
        content: str, 
        media_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not self.facebook_access_token or not self.facebook_page_id:
            return {"success": False, "error": "Facebook credentials not configured"}
        
        url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/feed"
        
        data = {
            "message": content,
            "access_token": self.facebook_access_token
        }
        
        # Add media if provided
        if media_urls:
            # For simplicity, using the first media URL
            data["link"] = media_urls[0]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "platform": "facebook"
                }
            else:
                return {
                    "success": False,
                    "error": f"Facebook API error: {response.text}",
                    "platform": "facebook"
                }
    
    async def _publish_to_instagram(
        self, 
        content: str, 
        media_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not self.instagram_access_token or not self.instagram_account_id:
            return {"success": False, "error": "Instagram credentials not configured"}
        
        # Instagram requires media for posts
        if not media_urls:
            return {"success": False, "error": "Instagram posts require media"}
        
        # Create media container first
        container_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media"
        
        container_data = {
            "image_url": media_urls[0],  # Using first media URL
            "caption": content,
            "access_token": self.instagram_access_token
        }
        
        async with httpx.AsyncClient() as client:
            # Create container
            container_response = await client.post(container_url, data=container_data)
            
            if container_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Instagram container creation failed: {container_response.text}",
                    "platform": "instagram"
                }
            
            container_id = container_response.json().get("id")
            
            # Publish the container
            publish_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media_publish"
            publish_data = {
                "creation_id": container_id,
                "access_token": self.instagram_access_token
            }
            
            publish_response = await client.post(publish_url, data=publish_data)
            
            if publish_response.status_code == 200:
                result = publish_response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "platform": "instagram"
                }
            else:
                return {
                    "success": False,
                    "error": f"Instagram publish failed: {publish_response.text}",
                    "platform": "instagram"
                }
    
    async def _publish_to_tiktok(
        self, 
        content: str, 
        media_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        # TikTok API implementation would go here
        # For now, returning a placeholder
        return {
            "success": False,
            "error": "TikTok API integration not yet implemented",
            "platform": "tiktok"
        }
    
    async def _publish_video_to_facebook(
        self,
        content: str,
        video_url: str,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.facebook_access_token or not self.facebook_page_id:
            return {"success": False, "error": "Facebook credentials not configured"}
        
        url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/videos"
        
        data = {
            "file_url": video_url,
            "description": content or video_description or "",
            "title": video_title or "",
            "access_token": self.facebook_access_token
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # Extended timeout for video upload
            response = await client.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "platform": "facebook"
                }
            else:
                return {
                    "success": False,
                    "error": f"Facebook video upload error: {response.text}",
                    "platform": "facebook"
                }
    
    async def _publish_video_to_instagram(
        self,
        content: str,
        video_url: str,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.instagram_access_token or not self.instagram_account_id:
            return {"success": False, "error": "Instagram credentials not configured"}
        
        # Create video container
        container_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media"
        
        container_data = {
            "media_type": "VIDEO",
            "video_url": video_url,
            "caption": content or video_description or "",
            "access_token": self.instagram_access_token
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Create container
            container_response = await client.post(container_url, data=container_data)
            
            if container_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Instagram video container creation failed: {container_response.text}",
                    "platform": "instagram"
                }
            
            container_id = container_response.json().get("id")
            
            # Wait for video processing (Instagram requirement)
            await asyncio.sleep(10)  # Basic wait, in production should poll status
            
            # Publish the container
            publish_url = f"https://graph.facebook.com/v18.0/{self.instagram_account_id}/media_publish"
            publish_data = {
                "creation_id": container_id,
                "access_token": self.instagram_access_token
            }
            
            publish_response = await client.post(publish_url, data=publish_data)
            
            if publish_response.status_code == 200:
                result = publish_response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "platform": "instagram"
                }
            else:
                return {
                    "success": False,
                    "error": f"Instagram video publish failed: {publish_response.text}",
                    "platform": "instagram"
                }
    
    async def _publish_video_to_tiktok(
        self,
        content: str,
        video_url: str,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        video_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish video to TikTok using Content Posting API
        Requires TikTok Content Posting API approval and proper authentication
        """
        if not self.tiktok_access_token or not self.tiktok_account_id:
            return {"success": False, "error": "TikTok credentials not configured", "platform": "tiktok"}

        try:
            from .file_manager import privacy_uploader

            # Use privacy-compliant uploader
            async def upload_to_tiktok(temp_file_path: str):
                # Step 1: Upload video to TikTok
                upload_result = await self._upload_video_to_tiktok(temp_file_path)

                if not upload_result.get("success"):
                    raise Exception(f"TikTok video upload failed: {upload_result.get('error')}")

                # Step 2: Create post with uploaded video
                post_result = await self._create_tiktok_post(
                    upload_result["video_id"],
                    content or video_description or "",
                    video_title,
                    video_tags
                )

                return post_result

            # Process upload with automatic cleanup
            result = await privacy_uploader.process_video_upload(
                video_url,
                upload_to_tiktok,
                cleanup_immediately=True
            )

            if result["success"]:
                return result["result"]
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "platform": "tiktok"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"TikTok posting error: {str(e)}",
                "platform": "tiktok"
            }

    async def _download_video_temporarily(self, video_url: str) -> str:
        """Download video file temporarily for TikTok upload"""
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_filename = f"tiktok_upload_{int(time.time())}.mp4"
        temp_path = os.path.join(temp_dir, temp_filename)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            # Write file synchronously for now (can be optimized with aiofiles later)
            with open(temp_path, 'wb') as f:
                f.write(response.content)

        return temp_path

    async def _upload_video_to_tiktok(self, video_file_path: str) -> Dict[str, Any]:
        """Upload video file to TikTok servers"""
        # Step 1: Initialize upload
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"

        init_data = {
            "post_info": {
                "title": "Video Upload",
                "privacy_level": "SELF_ONLY",  # Private draft as per privacy policy
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": os.path.getsize(video_file_path),
                "chunk_size": 10485760,  # 10MB chunks
                "total_chunk_count": 1
            }
        }

        headers = {
            "Authorization": f"Bearer {self.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Initialize upload
            init_response = await client.post(init_url, json=init_data, headers=headers)

            if init_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"TikTok upload initialization failed: {init_response.text}"
                }

            init_result = init_response.json()
            publish_id = init_result["data"]["publish_id"]
            upload_url = init_result["data"]["upload_url"]

            # Upload video file
            with open(video_file_path, 'rb') as video_file:
                upload_response = await client.put(
                    upload_url,
                    content=video_file.read(),
                    headers={"Content-Type": "video/mp4"}
                )

            if upload_response.status_code not in [200, 201]:
                return {
                    "success": False,
                    "error": f"TikTok video upload failed: {upload_response.text}"
                }

            return {
                "success": True,
                "publish_id": publish_id,
                "video_id": publish_id
            }

    async def _create_tiktok_post(
        self,
        publish_id: str,
        description: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create TikTok post with uploaded video"""

        # Prepare post data
        post_data = {
            "post_info": {
                "title": title or description[:100],  # TikTok title limit
                "description": description,
                "privacy_level": "SELF_ONLY",  # Private draft as per privacy policy
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False
            }
        }

        # Add hashtags if provided
        if tags:
            hashtags = " ".join([f"#{tag.replace('#', '')}" for tag in tags])
            post_data["post_info"]["description"] += f" {hashtags}"

        headers = {
            "Authorization": f"Bearer {self.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        publish_url = f"https://open.tiktokapis.com/v2/post/publish/video/init/"

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(publish_url, json=post_data, headers=headers)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result["data"]["publish_id"],
                    "platform": "tiktok",
                    "status": "draft"  # Always creates as draft per privacy policy
                }
            else:
                return {
                    "success": False,
                    "error": f"TikTok post creation failed: {response.text}",
                    "platform": "tiktok"
                }

    async def _cleanup_temporary_file(self, file_path: str):
        """Clean up temporary files as per privacy policy"""
        import os
        import asyncio

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Temporary file cleaned up: {file_path}")
        except Exception as e:
            print(f"Warning: Failed to cleanup temporary file {file_path}: {e}")
            # Schedule retry cleanup
            await asyncio.sleep(1)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass  # Final attempt, ignore if fails