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


@router.get("/account", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def account_page(request: Request):
    try:
        user_data = await fetch_user_data(request)


        data = {
            "site": await get_config(),
            "user": user_data,
            "stats": await get_stats_data(),
        }

        logger.debug(f"Account page data: {data}")

        response = templates.TemplateResponse(
            "/pages/account/index.html", 
            {
                "request": request,
                "data": data
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error loading Account page: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


ACCOUNT_PAGES = {
    "security": "/pages/account/security.html",
    "settings": "/pages/account/settings.html",
    "payments": "/pages/account/payments.html",
    "membership": "/pages/account/membership.html",
    "routine": "/pages/account/routine.html",
}

@router.get("/account/{page_name}", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def account_page_detail(request: Request, page_name: str):
    try:
        user_data = await fetch_user_data(request)

        if page_name not in ACCOUNT_PAGES:
            raise HTTPException(status_code=404, detail="Page not found")

        data = {
            "site": await get_config(),
            "user": user_data,
            "stats": await get_stats_data(),
        }

        logger.debug(f"Account page detail data: {data}")

        response = templates.TemplateResponse(
            ACCOUNT_PAGES.get(page_name),
            {
                "request": request,
                "data": data
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error loading Account page detail: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")
