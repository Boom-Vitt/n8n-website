from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 3600):
        super().__init__(app)
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds (default: 1 hour)
        self.clients = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Only apply rate limiting to API endpoints
        if not request.url.path.startswith("/api/") and not request.url.path.startswith("/webhook/"):
            return await call_next(request)
        
        # Get API key from query params or headers
        api_key = request.query_params.get("api_key")
        if not api_key:
            api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return await call_next(request)
        
        # Clean old requests
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)
        self.clients[api_key] = [
            timestamp for timestamp in self.clients[api_key] 
            if timestamp > cutoff
        ]
        
        # Check rate limit
        if len(self.clients[api_key]) >= self.calls:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.calls} requests per {self.period} seconds allowed",
                    "retry_after": self.period
                }
            )
        
        # Add current request timestamp
        self.clients[api_key].append(now)
        
        return await call_next(request)

class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.protected_paths = ["/api/", "/webhook/"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check if path needs API key validation
        needs_validation = any(
            request.url.path.startswith(path) 
            for path in self.protected_paths
        )
        
        if not needs_validation:
            return await call_next(request)
        
        # Skip validation for test endpoints
        if request.url.path == "/n8n/test-connection":
            return await call_next(request)
        
        # Get API key
        api_key = request.query_params.get("api_key")
        if not api_key:
            api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "API key required",
                    "message": "Please provide API key via 'api_key' query parameter or 'X-API-Key' header"
                }
            )
        
        return await call_next(request)