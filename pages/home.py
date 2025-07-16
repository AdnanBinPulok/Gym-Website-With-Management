from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi import HTTPException
import json
import random
import string
from cachetools import TTLCache
import traceback
from fastapi import Depends

router = APIRouter()
templates = Jinja2Templates(directory="static")

from services.logging import logger
import datetime

from modules.rate_limiter import RateLimiter

rate_limiter = RateLimiter(times=30, seconds=5)

from modules.data import get_config, get_schedule_data, get_gallery_data
from modules.functions import fetch_user_data, get_stats_data

@router.get("/", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def home_page(request: Request):
    try:
        user_data = await fetch_user_data(request)


        data = {
            "site": await get_config(),
            "user": user_data,
            "schedule": await get_schedule_data(),
            "stats": await get_stats_data(),
            "gallery": await get_gallery_data(),
        }

        logger.debug(f"Home page data: {data}")

        response = templates.TemplateResponse(
            "/pages/home.html", 
            {
                "request": request,
                "data": data
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error loading home page: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")