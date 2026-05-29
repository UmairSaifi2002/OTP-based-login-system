"""
Authentication Middleware

Protects API endpoints by verifying JWT tokens.
Extracts the user ID from valid tokens and makes it available to endpoints.

HOW IT WORKS:
1. Reads the "Authorization" header from the request
2. Extracts the JWT token (removes "Bearer " prefix)
3. Verifies the token using verify_access_token()
4. Extracts the user ID
5. Attaches the user ID to the request state

Usage in endpoints:
    user_id = request.state.user_id
    if not user_id:
        raise HTTPException(401, "Not authenticated")
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.v1.security import get_user_id_from_token
from app.utils.v1.loggers import logger


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that verifies JWT tokens on protected routes.
    
    This runs BEFORE every request reaches the endpoint.
    If the token is invalid, the request is rejected with 401.
    If the token is valid, the user ID is attached to the request.
    """
    
    # ============================================
    # ROUTES THAT DON'T NEED AUTHENTICATION
    # ============================================
    # These paths are PUBLIC - anyone can access them

    PUBLIC_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redocs",
        "/openapi.json",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/verify-otp",
    ]

    async def dispatch(self, request: Request, call_next):
        """
        Process every incoming request.
        
        Args:
            request: The incoming HTTP request
            call_next: Function to call the next middleware/endpoint
        
        Returns:
            Response from the next layer
        """
        
        # ============================================
        # STEP 1: Skip authentication for public paths
        # ============================================
        # If the request path is in PUBLIC_PATHS, let it through
        # without checking for a token
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Also allow OPTIONS requests (for CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # ============================================
        # STEP 2: Extract the Authorization header
        # ============================================
        # The header looks like: "Bearer eyJhbGciOiJIUzI1NiJ9..."
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"Missing Authorization header for path: {request.url.path}")
            raise HTTPException(
                status_code = 401,
                detail = "Not authenticated. Please provide a valid token/ Authorization header missing"
            )
        
        # ============================================
        # STEP 3: Extract the token
        # ============================================
        # Remove "Bearer " prefix to get the raw token
        if not auth_header.startswith("Bearer "):
            logger.warning(f"Invalid Authorization header format for path: {request.url.path}")
            raise HTTPException(
                status_code = 401,
                detail = "Invalid token format. Expected 'Bearer <token>'"
            )
        
        token = auth_header.replace("Bearer ", "")

        # ============================================
        # STEP 4: Verify the token
        # ============================================
        user_id = get_user_id_from_token(token)

        if not user_id:
            logger.warning(f"Invalid or Expired token for path: {request.url.path}")
            raise HTTPException(
                status_code = 401,
                detail = "Invalid or expired token. Please login again."
            )
        
        # ============================================
        # STEP 5: Attach user ID to the request
        # ============================================
        # request.state is a place to store data that
        # endpoints can access later
        request.state.user_id = user_id
        logger.debug(f"Authenticated user_id: {user_id} for path: {request.url.path}")

        # ============================================
        # STEP 6: Continue to the endpoint
        # ============================================
        response = await call_next(request)
        return response
    
        











