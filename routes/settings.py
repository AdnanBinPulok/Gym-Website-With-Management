from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi import HTTPException
import json
import random
import string
from cachetools import TTLCache
import traceback
import re
from fastapi import Depends

from services.logging import logger
from services.database import sessions, users, payments
import datetime
from passlib.hash import pbkdf2_sha256

from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests

from aiocache import cached


from modules.data import get_config, get_timezone, get_payment_methods
from modules.functions import fetch_user_data,generate_session_id
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)



@router.post("/api/save-settings", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def save_settings(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized")

        data = await request.json()
        full_name = data.get("full_name")

        # Validate email format
        if not full_name:
            raise HTTPException(status_code=400, detail="Full name is required")

        updated = await users.update(
            {'id': user_data.get("id")},
            full_name=full_name,
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )

        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update settings")

        return JSONResponse(content={"success": True, "message": "Settings updated successfully"}, status_code=200)

    except Exception as e:
        logger.error(f"Error saving settings: {traceback.format_exc()}")
        return JSONResponse(content={"success": False, "message": "Internal server error"}, status_code=500)
    
    