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


from modules.data import get_config, get_timezone, get_payment_methods,save_config
from modules.functions import fetch_user_data,generate_session_id
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)

# social_links = [
#    {
#        "name": "Facebook",
#        "url": "https://www.facebook.com/people/Aesthetic-Fitness-Gym/100086470634432/",
#        "icon": "fab fa-facebook-f"
#    }
#]

@router.get("/api/get-social-links", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_social_links(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"status": "error", "message": "Unauthorized"},
                status_code=401
            )
        
        if not user_data.get('is_admin', False):
            return JSONResponse(
                content={"status": "error", "message": "Forbidden"},
                status_code=403
            )
        
        config_data = await get_config()

        social_links = config_data.get("social_links", {})
        return JSONResponse(content={"success": True, "data": social_links})
    except Exception as e:
        logger.error(f"Error fetching social links: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )

def validate_social_links_data(data):
    if not isinstance(data, list):
        return False, "Invalid data format"

    for social_ in data:
        if not isinstance(social_, dict):
            return False, "Invalid social link format"

        if "name" not in social_ or "url" not in social_ or "icon" not in social_:
            return False, "Missing required fields in social link"

        if not isinstance(social_["name"], str) or not isinstance(social_["url"], str) or not isinstance(social_["icon"], str):
            return False, "Invalid field types in social link"

    return True, ""


@router.post("/api/save-social-links", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def save_social_links(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )
        
        if not user_data.get('is_admin', False):
            return JSONResponse(
                content={"success": False, "message": "Forbidden"},
                status_code=403
            )

        data = await request.json()
        
        is_valid, error_message = validate_social_links_data(data)
        if not is_valid:
            return JSONResponse(
                content={"success": False, "message": error_message},
                status_code=400
            )

        config_data = await get_config()
        config_data["social_links"] = data

        # Save the updated config data
        await save_config(config_data)

        return JSONResponse(content={"success": True, "message": "Social links updated successfully"})
    except Exception as e:
        logger.error(f"Error saving social links: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )