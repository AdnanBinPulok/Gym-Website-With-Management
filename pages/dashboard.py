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


@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def dashboard_page(request: Request):
    try:
        user_data = await fetch_user_data(request)


        data = {
            "site": await get_config(),
            "user": user_data,
            "stats": await get_stats_data(),
        }

        logger.debug(f"dashboard page data: {data}")

        response = templates.TemplateResponse(
            "/pages/dashboard/index.html", 
            {
                "request": request,
                "data": data
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error loading dashboard page: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


dashboard_PAGES = {
    "users": "/pages/dashboard/users.html",
    "payments": "/pages/dashboard/payments.html",
    "gallery": "/pages/dashboard/gallery.html",
    "schedule": "/pages/dashboard/schedule.html",
    "settings": "/pages/dashboard/settings.html"
}

@router.get("/dashboard/{page_name}", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def dashboard_page_detail(request: Request, page_name: str):
    try:
        user_data = await fetch_user_data(request)

        if page_name not in dashboard_PAGES:
            raise HTTPException(status_code=404, detail="Page not found")

        data = {
            "site": await get_config(),
            "user": user_data,
            "stats": await get_stats_data(),
        }

        logger.debug(f"dashboard page detail data: {data}")

        response = templates.TemplateResponse(
            dashboard_PAGES.get(page_name),
            {
                "request": request,
                "data": data
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error loading dashboard page detail: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dashboard/edit-user/{user_id}", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def edit_user_page(request: Request, user_id: str):
    try:
        user_data = await fetch_user_data(request)

        data = {
            "site": await get_config(),
            "user": user_data,
            "stats": await get_stats_data(),
        }

        logger.debug(f"edit user page data: {data}")

        response = templates.TemplateResponse(
            "/pages/dashboard/edit_user.html",
            {
                "request": request,
                "data": data,
                "user_id": user_id
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error loading edit user page: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")
