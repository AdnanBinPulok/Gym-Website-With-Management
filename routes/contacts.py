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

@router.get("/api/get-contacts", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_contacts(request: Request):
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

        config_data = await get_config()
        contact_info = config_data.get("contact", {})

        return JSONResponse(content={"success": True, "data": contact_info})
    except Exception as e:
        logger.error(f"Error fetching contact info: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    


@router.post("/api/update-contacts", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def update_contacts(request: Request):
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

        config_data = await get_config()
        config_data["contact"] = {
            "email": data.get("email", None),
            "phone": data.get("phone", None),
            "whatsapp": data.get("whatsapp", None)
        }

        # Save the updated config data
        await save_config(config_data)

        return JSONResponse(content={"success": True, "message": "Contact info updated successfully"})
    except Exception as e:
        logger.error(f"Error updating contact info: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )