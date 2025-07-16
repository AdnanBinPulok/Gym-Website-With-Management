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


# users = Table(
#     name="users",
#     connection=connection,
#     columns=[
#         Column(name="id",type=DataType.SERIAL().primary_key().unique().not_null()),

#         Column(name="card_id",type=DataType.VARCHAR(length=255).unique()),

#         Column(name="full_name",type=DataType.VARCHAR(length=255)),
#         Column(name="username",type=DataType.VARCHAR(length=255).unique()),

#         Column(name="email",type=DataType.VARCHAR(length=255).unique().not_null()),
#         Column(name="phone",type=DataType.VARCHAR(length=255).unique()),

#         Column(name="email_verified",type=DataType.BOOLEAN().default('false')),
#         Column(name="phone_verified",type=DataType.BOOLEAN().default('false')),

#         Column(name="password",type=DataType.VARCHAR(length=255)),

#         Column(name="role",type=DataType.VARCHAR(length=255).not_null().default('user')),

#         Column(name="avatar_url",type=DataType.VARCHAR(length=255)),

#         Column(name="balance",type=DataType.DOUBLE_PRECISION().default('0.0')),

#         Column(name="routine",type=DataType.TEXT()), # User's workout routine in text format



#         Column(name="membership_active",type=DataType.BOOLEAN().default('false')), # whether the user has an active membership

#         Column(name="membership_type",type=DataType.VARCHAR(length=255).default('basic')), # can be basic, premium, vip, etc.

#         Column(name="membership_start_date",type=DataType.TIMESTAMPTZ()), # start date for the membership
#         Column(name="membership_end_date",type=DataType.TIMESTAMPTZ()), # end date for the membership

#         Column(name="membership_payment_cycle",type=DataType.VARCHAR(length=255).default('monthly')), # can be monthly, yearly, etc. or 6 Months, 1 Year, etc.

#         Column(name="membership_renewal_date",type=DataType.TIMESTAMPTZ()), # renewal date for the membership
#         Column(name="membership_renewal_price",type=DataType.DOUBLE_PRECISION().default('0.0')), # renewal price for the membership
#         Column(name="membership_renewal_by",type=DataType.VARCHAR(length=255).default('user')), # can be user or admin




#         Column(name="membership_cancelled",type=DataType.BOOLEAN().default('false')),
#         Column(name="membership_cancelled_reason",type=DataType.VARCHAR(length=255)),
#         Column(name="membership_cancelled_at",type=DataType.TIMESTAMPTZ()),
#         Column(name="membership_cancelled_by",type=DataType.VARCHAR(length=255)),

#         Column(name="last_login",type=DataType.TIMESTAMPTZ()),
#         Column(name="updated_at",type=DataType.TIMESTAMPTZ()),
#         Column(name="created_at",type=DataType.TIMESTAMPTZ().default('CURRENT_TIMESTAMP'))
#     ],
#     cache=True,
#     cache_key="id",
#     cache_ttl=5,
#     cache_maxsize=1000
# )

@router.get("/api/get-membership-state", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def membership_page(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized")
        

        modified_user_data = {
            "card_id": user_data.get("card_id"),
            "membership_active": user_data.get("membership_active", False),
            "membership_type": user_data.get("membership_type", "basic"),
            "membership_start_date": user_data.get("membership_start_date"),
            "membership_end_date": user_data.get("membership_end_date"),
            "membership_payment_cycle": user_data.get("membership_payment_cycle", "monthly"),
            "membership_renewal_date": user_data.get("membership_renewal_date"),
            "membership_renewal_price": user_data.get("membership_renewal_price", 0.0),
            "membership_renewal_by": user_data.get("membership_renewal_by", "user"),
            "membership_cancelled": user_data.get("membership_cancelled", False),
            "membership_cancelled_reason": user_data.get("membership_cancelled_reason", None),
            "membership_cancelled_at": user_data.get("membership_cancelled_at"),
            "membership_cancelled_by": user_data.get("membership_cancelled_by", None)
        }

        return JSONResponse(
            content={
                "success": True,
                "message": "Membership state fetched successfully",
                "data": modified_user_data
            }
        )
    except Exception as e:
        logger.error(f"Error fetching membership state: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "error": str(e)
            }
        )