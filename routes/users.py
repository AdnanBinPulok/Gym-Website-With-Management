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


from modules.data import get_config, get_timezone, get_payment_methods, get_subscriptions_plans
from modules.functions import fetch_user_data,generate_session_id, send_renewal_notification
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp



from dateutil.relativedelta import relativedelta

router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)

from pgconnect.Filters import Filters








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

@cached(ttl=5)
async def fetch_users(
    page: int = 1,
    limit: int = 10,
    order_by: str = "id",
    order: str = "asc",
    search_query = None,
    where_conditions: dict = None
):
    try:
        if search_query:
            users_data_raw = await users.search(
                by=['id', 'card_id', 'full_name', 'username', 'email', 'phone'],
                keyword=search_query,
                page=page,
                limit=limit,
                order_by=order_by,
                order=order,
                where=where_conditions
            )
            count_total = await users.count_search(
                by=['id', 'card_id', 'full_name', 'username', 'email', 'phone'],
                keyword=search_query,
                where=where_conditions
            )
        else:
            users_data_raw = await users.get_page(
                page=page,
                limit=limit,
                order_by=order_by,
                order=order,
                where=where_conditions
            )
            count_total = await users.count(**where_conditions)
        
        users_data = []
        local_timezone = await get_timezone()
        for user in users_data_raw:
            user = dict(user)
            for key, value in user.items():
                if isinstance(value, datetime.datetime):
                    user[key] = value.astimezone(local_timezone).isoformat() if value else None
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    user[key] = str(value)
                else:
                    user[key] = value
            del user['password']  # Remove password from the response
            users_data.append(user)

        return users_data, count_total
    except Exception as e:
        logger.error(f"Error fetching users: {traceback.format_exc()}")
        return [], 0


# GET /api/get-users endpoint to fetch users with pagination, filtering, and sorting
# Query parameters:
# - page: Page number for pagination (default: 1)
# - limit: Number of users per page (default: 10)
# - order_by: Column to order by (default: "id")
# - order: Order direction, "asc" or "desc" (default: "asc")
# - user_id: Filter by user ID
# - card_id: Filter by card ID
# - full_name: Filter by full name
# - username: Filter by username
# - email: Filter by email
# - phone: Filter by phone number
# - membership_active: Filter by active membership (true/false)
# - membership_type: Filter by membership type (e.g., "basic", "premium")
# - membership_cancelled: Filter by cancelled membership (true/false)
# - search: Search query 
@router.get("/api/get-users", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_users(request: Request):
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
        
        page = int(request.query_params.get("page", 1)) 
        limit = int(request.query_params.get("limit", 10))
        order_by = request.query_params.get("order_by", "id")
        order = request.query_params.get("order", "asc").lower()
        if order not in ["asc", "desc"]:
            return JSONResponse(
                content={"success": False, "message": "Invalid order parameter"},
                status_code=400
            )
        
        user_id = int(request.query_params.get("user_id", None)) if request.query_params.get("user_id") else None
        card_id = request.query_params.get("card_id", None)
        full_name = request.query_params.get("full_name", None)
        username = request.query_params.get("username", None)
        email = request.query_params.get("email", None)
        phone = request.query_params.get("phone", None)
        membership_active = request.query_params.get("membership_active", None)
        membership_type = request.query_params.get("membership_type", None)
        membership_cancelled = request.query_params.get("membership_cancelled", None)

        search_query = request.query_params.get("search", None)

        where_conditions = {}
        if user_id is not None:
            where_conditions["id"] = user_id
        if card_id:
            where_conditions["card_id"] = card_id
        if full_name:
            where_conditions["full_name"] = full_name
        if username:
            where_conditions["username"] = username
        if email:
            where_conditions["email"] = email
        if phone:
            where_conditions["phone"] = phone
        if membership_active is not None:
            where_conditions["membership_active"] = membership_active.lower() == "true"
        if membership_type:
            where_conditions["membership_type"] = membership_type
        if membership_cancelled is not None:
            where_conditions["membership_cancelled"] = membership_cancelled.lower() == "true"
        # Fetch total count of users matching the filters

        users_data, count_total = await fetch_users(
            page=page,
            limit=limit,
            order_by=order_by,
            order=order,
            search_query=search_query,
            where_conditions=where_conditions
        )


        data = {
            "success": True,
            "data": users_data,
            "count_total": count_total
        }
        logger.debug(f"Dashboard stats data: {data}")
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    


# /api/create-user endpoint to create a new user
# Requires admin access
# Body parameters:
# - full_name: Full name of the user (required)
# - username: Username of the user (required)
# - email: Email of the user (required)
# - card_id: Card ID of the user (optional, can be auto-generated)
# - phone: Phone number of the user (optional)
# - password: none auto generate
@router.post("/api/create-user", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def create_user(request: Request):
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

        data = await request.json()
        full_name = str(data.get("full_name", "")).strip() if data.get("full_name") else None
        username = str(data.get("username", "")).strip() if data.get("username") else None
        email = str(data.get("email", "")).strip() if data.get("email") else None
        phone = str(data.get("phone", "")).strip() if data.get("phone") else None
        card_id = str(data.get("card_id", "")).strip() if data.get("card_id") else None

        if not full_name or not username or not email:
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )
        
        # Check for existing user with same email or username
        existing_user_by_email = await users.get(email=email)
        if existing_user_by_email:
            return JSONResponse(
                content={"success": False, "message": "User with this email already exists"},
                status_code=400
            )
        
        existing_user_by_username = await users.get(username=username)
        if existing_user_by_username:
            return JSONResponse(
                content={"success": False, "message": "User with this username already exists"},
                status_code=400
            )
        
        if card_id:
            card_id_exists = await users.get(card_id=card_id)
            if card_id_exists:
                return JSONResponse(
                    content={"success": False, "message": "User with this card ID already exists"},
                    status_code=400
                )

        new_user = {
            "full_name": full_name,
            "username": username,
            "email": email,
            "phone": phone,
            "card_id": card_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }

        inserted = await users.insert(**new_user)

        if not inserted:
            return JSONResponse(
                content={"success": False, "message": "Failed to create user"},
                status_code=500
            )

        return JSONResponse(
            content={"success": True, "message": "User created successfully", "user_id": inserted.get("id")},
            status_code=201
        )
    except Exception as e:
        logger.error(f"Error creating user: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )












async def fetch_user_info(user_id: int):
    try:
        user = await users.get(id=user_id)
        if not user:
            return None
        
        user = dict(user)
        local_timezone = await get_timezone()
        for key, value in user.items():
            if isinstance(value, datetime.datetime):
                user[key] = value.astimezone(local_timezone).isoformat() if value else None
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                user[key] = str(value)
            else:
                user[key] = value
        del user['password']  # Remove password from the response
        return user
    except Exception as e:
        logger.error(f"Error fetching user info: {traceback.format_exc()}")
        return None


# GET /api/get-user endpoint to fetch user info by user_id
# Query parameters:
# - user_id: ID of the user to fetch
# Returns:
# - 200 OK with user info if found
@router.get("/api/get-user", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_user(request: Request):
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

        user_id = int(request.query_params.get("user_id", None)) if request.query_params.get("user_id") else None
        if user_id is None:
            return JSONResponse(
                content={"success": False, "message": "Missing user_id parameter"},
                status_code=400
            )

        user_info = await fetch_user_info(user_id)
        if not user_info:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        return JSONResponse(
            content={"success": True, "data": user_info},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error getting user info: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    


@router.post("/api/update-user-mail-or-phone-or-cardid", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def update_user_mail_or_phone_or_card_id(request: Request):
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

        data = await request.json()
        user_id = int(data.get("id", None)) if data.get("id") else None
        email = str(data.get("email", "")).strip() if data.get("email") else None
        phone = str(data.get("phone", "")).strip() if data.get("phone") else None
        card_id = str(data.get("card_id", "")).strip() if data.get("card_id") else None

        if not user_id or (not email and not phone and not card_id):
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )
        
        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        # IF TARGET USER A SUPERADMIN CAN'T UPDATE
        if target_user.get("role") == "superadmin":
            return JSONResponse(
                content={"success": False, "message": "Cannot update superadmin user"},
                status_code=403
            )

        update_fields = {}
        if email:
            update_fields["email"] = email
        if phone:
            update_fields["phone"] = phone
        if card_id:
            update_fields["card_id"] = card_id

        updated = await users.update({'id':user_id}, **update_fields)
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to update user info"},
                status_code=500
            )
        

        return JSONResponse(
            content={"success": True, "message": "User info updated successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error updating user info: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    

@router.post('/api/update-routine', response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def update_routine(request: Request):
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

        data = await request.json()
        user_id = int(data.get("id", None)) if data.get("id") else None
        routine = str(data.get("text", "")).strip() if data.get("text") else None

        if not user_id or not routine:
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )
        
        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        updated = await users.update({'id':user_id}, routine=routine)
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to update user routine"},
                status_code=500
            )
        
        return JSONResponse(
            content={"success": True, "message": "User routine updated successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error updating user routine: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    

@router.post("/api/update-membership", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def update_membership(request: Request):
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

        data = await request.json()

        # id
        # : 
        # 1
        # membership_active
        # : 
        # true
        # membership_end_date
        # : 
        # "2026-06-15T12:19:00.000Z"
        # membership_payment_cycle
        # : 
        # "monthly"
        # membership_renewal_date
        # : 
        # "2026-06-12T12:19:00.000Z"
        # membership_renewal_price
        # : 
        # 1001
        # membership_start_date
        # : 
        # "2025-06-17T12:18:00.000Z"
        # membership_type
        # : 
        # "Basic"

        user_id = int(data.get("id", None)) if data.get("id") else None
        membership_active = data.get("membership_active", None)
        membership_type = data.get("membership_type", None)

        membership_start_date = data.get("membership_start_date", None)
        membership_end_date = data.get("membership_end_date", None)
        membership_payment_cycle = data.get("membership_payment_cycle", None)
        membership_renewal_date = data.get("membership_renewal_date", None)
        membership_renewal_price = data.get("membership_renewal_price", None)

        
        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )
        

        update_fields = {}
        if membership_active is not None:
            update_fields["membership_active"] = membership_active
        if membership_type:
            update_fields["membership_type"] = membership_type
        if membership_start_date:
            try:
                membership_start_date = datetime.datetime.fromisoformat(membership_start_date) if membership_start_date else None
            except ValueError:
                return JSONResponse(
                    content={"success": False, "message": "Invalid membership_start_date format"},
                    status_code=400
                )
            update_fields["membership_start_date"] = membership_start_date
        if membership_end_date:
            try:
                membership_end_date = datetime.datetime.fromisoformat(membership_end_date) if membership_end_date else None
            except ValueError:
                return JSONResponse(
                    content={"success": False, "message": "Invalid membership_end_date format"},
                    status_code=400
                )
            update_fields["membership_end_date"] = membership_end_date
        if membership_payment_cycle:
            update_fields["membership_payment_cycle"] = membership_payment_cycle
        if membership_renewal_date:
            try:
                membership_renewal_date = datetime.datetime.fromisoformat(membership_renewal_date) if membership_renewal_date else None
            except ValueError:
                return JSONResponse(
                    content={"success": False, "message": "Invalid membership_renewal_date format"},
                    status_code=400
                )
            update_fields["membership_renewal_date"] = membership_renewal_date

        if membership_renewal_price:
            update_fields["membership_renewal_price"] = membership_renewal_price


        updated = await users.update({'id':user_id}, **update_fields)

        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to update user membership"},
                status_code=500
            )
        
        return JSONResponse(
            content={"success": True, "message": "User membership updated successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error updating user membership: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )





@router.post("/api/deactivate-user-membership", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def deactivate_user_membership(request: Request):
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

        data = await request.json()
        user_id = int(data.get("id", None)) if data.get("id") else None
        reason = str(data.get("reason", "")).strip() if data.get("reason") else None

        if not user_id or not reason:
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )
        
        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        # IF TARGET USER A SUPERADMIN CAN'T UPDATE
        if target_user.get("role") == "superadmin":
            return JSONResponse(
                content={"success": False, "message": "Cannot deactivate superadmin user"},
                status_code=403
            )

        updated = await users.update(
            {'id':user_id},
            membership_active=False,
            membership_type=None,
            membership_end_date=None,
            membership_payment_cycle=None,
            membership_renewal_date=None,
            membership_renewal_price=None,
            membership_cancelled=True,
            membership_cancelled_reason=reason, 
            membership_cancelled_at=datetime.datetime.now(datetime.timezone.utc),
            membership_cancelled_by=f"#{user_data.get('id', '')} {user_data.get('username', 'unknown')}"
        )
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to deactivate user membership"},
                status_code=500
            )
        
        return JSONResponse(
            content={"success": True, "message": "User membership deactivated successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error deactivating user membership: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    


@router.post("/api/active-user-membership", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def activate_user_membership(request: Request):
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

        data = await request.json()
        # id
        # : 
        # 2
        # membership_type
        # : 
        # "Basic"
        # months
        # : 
        # 1
        # renewal_notice_days
        # : 
        # 7
        user_id = int(data.get("id", None)) if data.get("id") else None
        membership_type = str(data.get("membership_type", "")).strip().lower() if data.get("membership_type") else None
        months = int(data.get("months", 0)) if data.get("months") else 0
        renewal_notice_days = int(data.get("renewal_notice_days", 0)) if data.get("renewal_notice_days") else 0

        if not user_id or not membership_type or months <= 0 or renewal_notice_days < 0:
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )

        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        # IF TARGET USER A SUPERADMIN CAN'T UPDATE
        if target_user.get("role") == "superadmin":
            return JSONResponse(
                content={"success": False, "message": "Cannot activate superadmin user"},
                status_code=403
            )
        
        all_membership_types_raw = await get_subscriptions_plans()
        all_membership_types = all_membership_types_raw.get('subscriptions_plans', [])

        def get_membership_plan_by_type(membership_type):
            for plan in all_membership_types:
                if plan.get("value") == membership_type:
                    return plan
            return None
        

        membership_type_plan = get_membership_plan_by_type(membership_type)
        if not membership_type_plan:
            return JSONResponse(
                content={"success": False, "message": "Invalid membership type"},
                status_code=400
            )
        
        extra_fields = {}
        if not membership_type_plan.get("membership_start_date"):
            extra_fields["membership_start_date"] = datetime.datetime.now(datetime.timezone.utc)

        membership_end_date = datetime.datetime.now(datetime.timezone.utc) + relativedelta(months=months)
        membership_renewal_date = membership_end_date - datetime.timedelta(days=renewal_notice_days)

        updated = await users.update(
            {'id': user_id},
            membership_active=True,
            membership_type=membership_type_plan.get("value").capitalize(),
            membership_end_date=membership_end_date,
            membership_payment_cycle=membership_type_plan.get("cycle", "monthly").capitalize(),
            membership_renewal_date=membership_renewal_date,
            membership_renewal_price=membership_type_plan.get("final_fee", 0.0),
            membership_cancelled=False,
            membership_cancelled_reason=None,
            membership_cancelled_at=None,
            membership_cancelled_by=None,
            **extra_fields
        )
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to activate user membership"},
                status_code=500
            )

        return JSONResponse(
            content={"success": True, "message": "User membership activated successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error activating user membership: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )

@router.get("/api/get-subscriptions-names", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_subscriptions_names(request: Request):
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

        subscriptions_plans = await get_subscriptions_plans()
        subscription_names = [sub.get("value") for sub in subscriptions_plans.get('subscriptions_plans', []) if sub.get("value")]
        return JSONResponse(
            content={"success": True, "data": subscription_names},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error fetching subscription names: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )




@router.post("/api/reset-membership", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def reset_membership(request: Request):
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

        data = await request.json()
        user_id = int(data.get("id", None)) if data.get("id") else None

        if not user_id:
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )
        
        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        # IF TARGET USER A SUPERADMIN CAN'T UPDATE
        if target_user.get("role") == "superadmin":
            return JSONResponse(
                content={"success": False, "message": "Cannot reset superadmin user membership"},
                status_code=403
            )

        updated = await users.update(
            {'id':user_id},
            membership_active=False,
            membership_type=None,
            membership_start_date=None,
            membership_end_date=None,
            membership_payment_cycle=None,
            membership_renewal_date=None,
            membership_renewal_price=None,
            membership_renewal_by=None,
            membership_cancelled=False,
            membership_cancelled_reason=None, 
            membership_cancelled_at=None,
            membership_cancelled_by=None
        )
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to reset user membership"},
                status_code=500
            )
        
        return JSONResponse(
            content={"success": True, "message": "User membership reset successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error resetting user membership: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )
    

@router.post("/api/extend-user-membership", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def extend_user_membership(request: Request):
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

        data = await request.json()
        user_id = int(data.get("id", None)) if data.get("id") else None
        months = int(data.get("months", 0)) if data.get("months") else 0

        if not user_id or months <= 0:
            return JSONResponse(
                content={"success": False, "message": "Missing required parameters"},
                status_code=400
            )
        
        target_user = await users.get(id=user_id)
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )

        # IF TARGET USER A SUPERADMIN CAN'T UPDATE
        if target_user.get("role") == "superadmin":
            return JSONResponse(
                content={"success": False, "message": "Cannot extend superadmin user membership"},
                status_code=403
            )

        membership_end_date = target_user.get("membership_end_date")
        if not membership_end_date:
            return JSONResponse(
                content={"success": False, "message": "User does not have an active membership to extend"},
                status_code=400
            )
        
        # if not already active, return error
        if not target_user.get("membership_active"):
            return JSONResponse(
                content={"success": False, "message": "User membership is not active"},
                status_code=400
            )
        
        membership_renewal_date = target_user.get("membership_renewal_date")

        new_membership_end_date = membership_end_date + relativedelta(months=months)
        new_membership_renewal_date = (membership_renewal_date + relativedelta(months=months)) if membership_renewal_date else new_membership_end_date

        updated = await users.update(
            {'id':user_id},
            membership_end_date=new_membership_end_date,
            membership_renewal_date=new_membership_renewal_date,
            membership_renewal_by=f"#{user_data.get('id', '')} {user_data.get('username', 'unknown')}"
        )
        
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to extend user membership"},
                status_code=500
            )
        
        try:
            asyncio.create_task(
                send_renewal_notification(
                    user_id=user_id,
                    months_extended=months,
                    old_end_date=membership_end_date,
                    new_end_date=new_membership_end_date,
                )
            )
        except Exception as e:
            logger.error(f"Error sending renewal notification: {traceback.format_exc()}")

        return JSONResponse(
            content={"success": True, "message": "User membership extended successfully"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error extending user membership: {traceback.format_exc()}")
        return JSONResponse(
            content={"success": False, "message": "Internal server error"},
            status_code=500
        )