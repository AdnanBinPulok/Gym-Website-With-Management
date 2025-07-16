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

from pgconnect.Filters import Filters

@cached(ttl=5)
async def fetch_dashboard_stats():
    try:
        total_users = await users.count()

        expiring_soon_datetime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)

        expiring_soon_output = await users.query(
            "SELECT COUNT(*) FROM users WHERE membership_active = TRUE AND membership_renewal_date <= %s",
            (expiring_soon_datetime,)
        )

        data = {
            "total_members": total_users,
            "active_subscriptions": await users.count(membership_active=True),
            "expired_subscriptions": await users.count(membership_cancelled=True),
            "expiring_subscriptions": await users.count(
                membership_active=True,
                membership_renewal_date=Filters.Between(
                    from_value=None,
                    to_value=expiring_soon_datetime
                )
            ),
        }
        return data
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {traceback.format_exc()}")
        return None


@router.get("/api/get-dashboard-stats", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_dashboard_stats(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )
        
        if not user_data.get("is_admin"):
            return JSONResponse(
                content={"success": False, "message": "Forbidden: Admin access required"},
                status_code=403
            )


        data = {
            "success": True,
            "stats": await fetch_dashboard_stats()
        }
        logger.debug(f"Dashboard stats data: {data}")
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )