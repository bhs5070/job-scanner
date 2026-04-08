"""Google OAuth2 authentication router."""

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from src.common.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _sign_token(data: dict) -> str:
    """Create a simple signed token (HMAC-SHA256)."""
    settings = get_settings()
    secret = settings.OPENAI_API_KEY[:16]  # Use part of existing secret as signing key
    payload = json.dumps(data, sort_keys=True)
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}|{sig}"


def _verify_token(token: str) -> dict | None:
    """Verify and decode a signed token."""
    settings = get_settings()
    secret = settings.OPENAI_API_KEY[:16]
    try:
        payload, sig = token.rsplit("|", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(payload)
        # Check expiry (24 hours)
        if time.time() - data.get("iat", 0) > 86400:
            return None
        return data
    except Exception:
        return None


@router.get("/google/url")
async def google_login_url() -> dict:
    """Return the Google OAuth2 authorization URL."""
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"url": url}


@router.get("/google/callback")
async def google_callback(code: str) -> RedirectResponse:
    """Handle the Google OAuth2 callback."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_res.status_code != 200:
            logger.error(f"Token exchange failed: {token_res.text}")
            raise HTTPException(status_code=400, detail="Authentication failed")

        tokens = token_res.json()
        access_token = tokens.get("access_token")

        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_info = user_res.json()

    # Create signed auth cookie instead of URL params
    token_data = {
        "name": user_info.get("name", ""),
        "email": user_info.get("email", ""),
        "picture": user_info.get("picture", ""),
        "iat": int(time.time()),
    }
    auth_token = _sign_token(token_data)

    response = RedirectResponse(url="/")
    response.set_cookie(
        "auth_token", auth_token,
        httponly=False,  # Frontend needs to read it
        samesite="lax",
        max_age=86400,
    )
    return response


@router.get("/me")
async def get_current_user(auth_token: str = Cookie(default="")) -> dict:
    """Get current user info from auth cookie."""
    if not auth_token:
        return {"authenticated": False}

    data = _verify_token(auth_token)
    if not data:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "picture": data.get("picture", ""),
    }


@router.post("/logout")
async def logout() -> JSONResponse:
    """Clear auth cookie."""
    response = JSONResponse({"status": "ok"})
    response.delete_cookie("auth_token")
    return response
