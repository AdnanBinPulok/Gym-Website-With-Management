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

@router.get("/api/get-logo-and-favicon", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_logo_and_favicon(request: Request):
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
        logo_url = config_data.get("logo", "/images/logo.png")
        favicon_url = config_data.get("favicon", "/images/favicon.png")

        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "logo": logo_url,
                    "favicon": favicon_url
                }
            }
        )
    except Exception as e:
        logger.error(f"Error fetching logo and favicon: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )


@router.post("/api/change-logo-or-favicon", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def change_logo_or_favicon(request: Request):
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
        
        form_data = await request.form()
        upload_type = form_data.get("type",'logo')
        image = form_data.get("image")

        if upload_type == "logo":
            # save the image to /data/images/logo.png
            try:
                with open("data/images/logo.png", "wb") as f:
                    f.write(await image.read())
            except Exception as e:
                logger.error(f"Error saving logo image: {traceback.format_exc()}")
                return JSONResponse(
                    content={"success": False, "message": "Failed to save logo image"},
                    status_code=500
                )
        elif upload_type == "favicon":
            try:
                with open("data/images/favicon.png", "wb") as f:
                    f.write(await image.read())
            except Exception as e:
                logger.error(f"Error saving favicon image: {traceback.format_exc()}")
                return JSONResponse(
                    content={"success": False, "message": "Failed to save favicon image"},
                    status_code=500
                )
        else:
            return JSONResponse(
                content={"success": False, "message": "Invalid upload type"},
                status_code=400
            )

        return JSONResponse(
            content={"success": True, "message": "Logo and favicon updated successfully"}
        )
    except Exception as e:
        logger.error(f"Error changing logo or favicon: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )