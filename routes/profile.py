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
from services.database import sessions, users
import datetime
from passlib.hash import pbkdf2_sha256

from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests


from modules.data import get_config,get_timezone
from modules.functions import fetch_user_data,generate_session_id
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)


@router.post("/api/change-avatar", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def change_avatar(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized")

        form_data = await request.form()
        image = form_data.get("image")

        uploaded_file_data = await upload_file(bytes=image.file)

        if not uploaded_file_data.get("success"):
            raise HTTPException(status_code=400, detail=uploaded_file_data.get("message", "Failed to upload image"))
        
        file_url = uploaded_file_data.get("file_url")

        # Update user avatar in the database
        updated = await users.update(
            {'id': user_data.get("id")},
            avatar_url=file_url,
        )

        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update avatar in the database")

        # if old avatar_url exists, delete it
        try:
            if user_data.get("avatar_url"):
                logger.debug(f"Deleting old avatar: {user_data.get('avatar_url')}")
                asyncio.create_task(delete_image(user_data.get("avatar_url")))  # Fire and forget
        except Exception as e:
            logger.error(f"Error deleting old avatar: {traceback.format_exc()}")

        return JSONResponse(status_code=200, content={"message": "Avatar updated successfully"})
    except Exception as e:
        logger.error(f"Error changing avatar: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")