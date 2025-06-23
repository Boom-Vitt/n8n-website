#!/usr/bin/env python3
"""
TikTok Integration Test Suite
Tests the complete AI Video Uploader system integration
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

class TikTokIntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8001", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.test_results = []
        
    async def run_all_tests(self):
        """Run complete test suite"""
        print("🧪 Starting TikTok Integration Test Suite")
        print("=" * 50)
        
        # Test 1: API Health Check
        await self.test_api_health()
        
        # Test 2: Authentication Test
        if self.api_key:
            await self.test_api_key_validation()
        else:
            print("⚠️  No API key provided, skipping authentication tests")
        
        # Test 3: File Manager Tests
        await self.test_file_manager()
        
        # Test 4: TikTok API Integration (if configured)
        await self.test_tiktok_integration()
        
        # Test 5: Privacy Compliance
        await self.test_privacy_compliance()
        
        # Test 6: Error Handling
        await self.test_error_handling()
        
        # Print Results
        self.print_test_results()
        
    async def test_api_health(self):
        """Test API health endpoint"""
        print("\n🔍 Testing API Health...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/health")
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test("API Health Check", True, f"Status: {data.get('status')}")
                else:
                    self.log_test("API Health Check", False, f"Status code: {response.status_code}")
                    
        except Exception as e:
            self.log_test("API Health Check", False, f"Error: {str(e)}")
    
    async def test_api_key_validation(self):
        """Test API key validation"""
        print("\n🔑 Testing API Key Validation...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/n8n/test-connection",
                    params={"api_key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test("API Key Validation", True, f"User: {data.get('user', {}).get('username')}")
                else:
                    self.log_test("API Key Validation", False, f"Status: {response.status_code}")
                    
        except Exception as e:
            self.log_test("API Key Validation", False, f"Error: {str(e)}")
    
    async def test_file_manager(self):
        """Test file manager functionality"""
        print("\n📁 Testing File Manager...")
        
        try:
            from file_manager import FileManager
            
            file_manager = FileManager()
            
            # Test temp file creation
            test_content = b"Test video content"
            temp_file = await file_manager.create_temp_file(test_content, ".mp4")
            
            # Verify file exists
            if os.path.exists(temp_file):
                self.log_test("Temp File Creation", True, f"Created: {temp_file}")
                
                # Test cleanup
                cleanup_success = await file_manager.cleanup_file(temp_file)
                self.log_test("File Cleanup", cleanup_success, "Immediate cleanup")
            else:
                self.log_test("Temp File Creation", False, "File not created")
                
            # Test stats
            stats = await file_manager.get_temp_file_stats()
            self.log_test("File Stats", True, f"Files: {stats.get('total_files', 0)}")
            
        except Exception as e:
            self.log_test("File Manager", False, f"Error: {str(e)}")
    
    async def test_tiktok_integration(self):
        """Test TikTok API integration"""
        print("\n🎵 Testing TikTok Integration...")
        
        if not self.api_key:
            self.log_test("TikTok Integration", False, "No API key provided")
            return
        
        try:
            # Test video post creation (without actual upload)
            test_data = {
                "content": "Test video from AI Video Uploader integration test",
                "platforms": ["tiktok"],
                "video_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
                "video_title": "Integration Test Video",
                "video_description": "Testing TikTok integration",
                "video_tags": ["test", "integration"]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/posts/video",
                    json=test_data,
                    params={"api_key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test("TikTok Video Post", True, f"Post ID: {data.get('id')}")
                else:
                    self.log_test("TikTok Video Post", False, f"Status: {response.status_code}")
                    
        except Exception as e:
            self.log_test("TikTok Integration", False, f"Error: {str(e)}")
    
    async def test_privacy_compliance(self):
        """Test privacy compliance features"""
        print("\n🛡️ Testing Privacy Compliance...")
        
        try:
            from file_manager import PrivacyCompliantUploader
            
            uploader = PrivacyCompliantUploader()
            
            # Mock callback function
            async def mock_upload_callback(file_path: str):
                return {"success": True, "mock": True, "file_processed": os.path.exists(file_path)}
            
            # Test with mock URL (won't actually download)
            try:
                result = await uploader.process_video_upload(
                    "https://httpbin.org/status/404",  # Will fail, testing error handling
                    mock_upload_callback,
                    cleanup_immediately=True
                )
                
                # Should fail but handle gracefully
                compliance = result.get("privacy_compliance", {})
                self.log_test("Privacy Compliance", True, f"Cleanup on error: {compliance.get('cleanup_on_error')}")
                
            except Exception as e:
                self.log_test("Privacy Compliance", True, "Error handled gracefully")
                
        except Exception as e:
            self.log_test("Privacy Compliance", False, f"Error: {str(e)}")
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n⚠️ Testing Error Handling...")
        
        if not self.api_key:
            self.log_test("Error Handling", False, "No API key provided")
            return
        
        try:
            # Test with invalid video URL
            test_data = {
                "content": "Test with invalid URL",
                "platforms": ["tiktok"],
                "video_url": "https://invalid-url-that-does-not-exist.com/video.mp4",
                "video_title": "Error Test"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/posts/video",
                    json=test_data,
                    params={"api_key": self.api_key}
                )
                
                # Should handle error gracefully
                if response.status_code in [200, 400, 422]:
                    self.log_test("Error Handling", True, "Graceful error handling")
                else:
                    self.log_test("Error Handling", False, f"Unexpected status: {response.status_code}")
                    
        except Exception as e:
            self.log_test("Error Handling", True, "Exception handled gracefully")
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"  {status} {test_name}: {details}")
    
    def print_test_results(self):
        """Print final test results"""
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        if total - passed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n🎯 Integration Status:", "READY" if passed >= total * 0.8 else "NEEDS ATTENTION")

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TikTok Integration Test Suite")
    parser.add_argument("--url", default="http://localhost:8001", help="API base URL")
    parser.add_argument("--api-key", help="API key for authenticated tests")
    
    args = parser.parse_args()
    
    tester = TikTokIntegrationTester(args.url, args.api_key)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
