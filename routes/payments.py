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

from dateutil.relativedelta import relativedelta

from aiocache import cached


from modules.data import get_config, get_timezone, get_payment_methods
from modules.functions import fetch_user_data,generate_session_id, send_renewal_notification
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp

from modules.mail import send_mail, generate_renewal_email

from settings.config import EmailConfig



router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)

from pgconnect.Filters import Filters


@router.get("/api/get-payment-methods", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_payment_methods_route(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )

        data = {
            "success": True,
            "data": {
                "methods": await get_payment_methods()
            }
        }
        logger.debug(f"Payment methods data: {data}")
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        logger.error(f"Error getting payment methods: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "error": str(e)}
        )


@router.post("/api/submit-payment", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def submit_payment(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )

        data = await request.json()
        payment_method_id = str(data.get("payment_method_id")) if data.get("payment_method_id") else None
        transaction_id = str(data.get("transaction_id")) if data.get("transaction_id") else None
        amount = float(data.get("amount", 0)) if data.get("amount") else 0

        if not payment_method_id or not amount or not transaction_id:
            return JSONResponse(
                content={"success": False, "message": "Invalid payment data"},
                status_code=400
            )
        
        if amount <= 0:
            return JSONResponse(
                content={"success": False, "message": "Amount must be greater than zero"},
                status_code=400
            )
        
        payment_methods = await get_payment_methods()

        def is_valid_payment_method(method_id):
            return any(str(method.get("id")).lower() == str(method_id).lower() for method in payment_methods)

        if not is_valid_payment_method(payment_method_id):
            return JSONResponse(
                content={"success": False, "message": "Invalid payment method"},
                status_code=400
            )

        # transaction_id exists check
        existing_payment = await payments.get(
            transaction_id=transaction_id
        )
        if existing_payment:
            return JSONResponse(
                content={"success": False, "message": "Transaction ID already exists"},
                status_code=400
            )
        
        config_data = await get_config()
        
        inserted_data = await payments.insert(
            user_id=user_data.get("id"),
            amount=amount,
            currency=config_data.get("currency", {}).get('symbol', '$'),
            payment_method=payment_method_id,
            transaction_id=transaction_id,
            status="pending",  # Initial status
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        if not inserted_data:
            return JSONResponse(
                content={"success": False, "message": "Failed to insert payment data"},
                status_code=500
            )

        logger.debug(f"Payment submitted: {inserted_data}")
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Payment submitted successfully",
            "payment_id": inserted_data.get("id")
        })
    except Exception as e:
        logger.error(f"Error submitting payment: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "error": str(e)}
        )


@cached(ttl=2)
async def get_payments_data(
    page: int,
    limit: int,
    order_by: str,
    order: str,
    where_conditions: dict
):
    try:
        payments_data = await payments.get_page(
            page=page,
            limit=limit,
            order_by=order_by,
            order=order,
            where=where_conditions
        )
        total_count = await payments.count(**where_conditions)
        
        local_tz = await get_timezone()
        modified_payments_data = []
        for payment in payments_data:
            payment = dict(payment)
            for key, value in payment.items():
                if isinstance(value, datetime.datetime):
                    payment[key] = value.astimezone(local_tz).isoformat()
                elif isinstance(value, (int,float)) and not isinstance(value, bool):
                    payment[key] = str(value)
                else:
                    payment[key] = value
            modified_payments_data.append(payment)

        return modified_payments_data, total_count
    except Exception as e:
        logger.error(f"Error getting payments data: {traceback.format_exc()}")
        return [], 0


# GET /api/get-payments
# Query Parameters:
# - page: int (default=1)
# - limit: int (default=10)
# - order_by: str (default="created_at")
# - order: str (default="desc", values: "asc", "desc")
# - transaction_id: str (optional, filter by transaction ID)
# Response:
# - success: bool
# - data: list of payment records
# - total_count: int (total number of records matching the query)
@router.get("/api/get-payments", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_payments(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )

        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        order_by = request.query_params.get("order_by", "created_at")
        order = request.query_params.get("order", "desc").lower()
        if order not in ["asc", "desc"]:
            return JSONResponse(
                content={"success": False, "message": "Invalid order parameter"},
                status_code=400
            )
        
        transaction_id = request.query_params.get("transaction_id")

        where_conditions = {"user_id": user_data.get("id")}
        if transaction_id:
            where_conditions["transaction_id"] = transaction_id

        payments_data, total_count = await get_payments_data(
            page=page,
            limit=limit,
            order_by=order_by,
            order=order,
            where_conditions=where_conditions
        )

        return JSONResponse(
            content={"success": True, "data": payments_data, "total_count": total_count},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error getting payments: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "error": str(e)}
        )


# payments = Table(
#     name="payments",
#     connection=connection,
#     columns=[
#         Column(name="id", type=DataType.SERIAL().primary_key().unique().not_null()),
#         Column(name="user_id", type=DataType.BIGINT().not_null()),  # Foreign key to users table

#         Column(name="amount", type=DataType.DOUBLE_PRECISION().not_null()),
#         Column(name="currency", type=DataType.VARCHAR(length=10).not_null()),

#         Column(name="payment_method", type=DataType.VARCHAR(length=255).not_null()),
#         Column(name="transaction_id", type=DataType.VARCHAR(length=255).unique().not_null()),
        
#         Column(name="note", type=DataType.TEXT()),  # e.g., payment for membership, donation, etc.

#         Column(name="status", type=DataType.VARCHAR(length=50).not_null()),  # e.g., pending, completed, failed
#         Column(name="updated_by", type=DataType.VARCHAR(length=255)),  # e.g., user, admin
#         Column(name="updated_at", type=DataType.TIMESTAMPTZ()),
#         Column(name="created_at", type=DataType.TIMESTAMPTZ().default('CURRENT_TIMESTAMP'))
#     ],
#     cache=True,
#     cache_key="id",
#     cache_ttl=5,
#     cache_maxsize=1000
# )

# get /api/get-all-payments
# Query Parameters:
# - page: int (default=1)
# - limit: int (default=10)
# - order_by: str (default="created_at")
# - order: str (default="desc", values: "asc", "desc")
# - user_id: int (optional, filter by user ID)
# - transaction_id: str (optional, filter by transaction ID)
# Response: 
# - success: bool
# - data: list of payment records
@router.get("/api/get-all-payments", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_all_payments(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )
        
        if not user_data.get("is_admin", False):
            return JSONResponse(
                content={"success": False, "message": "Unauthorized access"},
                status_code=403
            )

        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        order_by = request.query_params.get("order_by", "created_at")
        order = request.query_params.get("order", "desc").lower()
        if order not in ["asc", "desc"]:
            return JSONResponse(
                content={"success": False, "message": "Invalid order parameter"},
                status_code=400
            )

        transaction_id = request.query_params.get("transaction_id")
        user_id = int(request.query_params.get("user_id", 0)) if request.query_params.get("user_id") else None
        status = request.query_params.get("status")
        method = request.query_params.get("method")

        where_conditions = {}
        if transaction_id:
            where_conditions["transaction_id"] = transaction_id
        if user_id:
            where_conditions["user_id"] = user_id
        if status:
            where_conditions["status"] = status
        if method:
            where_conditions["payment_method"] = method

        payments_data, total_count = await get_payments_data(
            page=page,
            limit=limit,
            order_by=order_by,
            order=order,
            where_conditions=where_conditions
        )

        all_user_ids_raw = set(payment.get("user_id") for payment in payments_data)
        all_user_ids = list(all_user_ids_raw)
        all_users_data_raw = await users.gets(id=Filters.In(all_user_ids))

        all_users_data = []

        for user in all_users_data_raw:
            modified_user = {
                "id": user.get("id"),
                "full_name": user.get("full_name"),
                "username": user.get("username"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "avatar_url": user.get("avatar_url")
            }
            all_users_data.append(modified_user)


        def get_user_by_id(user_id):
            for user in all_users_data:
                if int(user.get("id")) == int(user_id):
                    return user
            return None
        
        for payment in payments_data:
            payment["user"] = get_user_by_id(payment.get("user_id"))

        return JSONResponse(
            content={"success": True, "data": payments_data, "total_count": total_count},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error getting all payments: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "error": str(e)}
        )


@router.post("/api/reject-payment", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def reject_payment(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )
        
        if not user_data.get("is_admin", False):
            return JSONResponse(
                content={"success": False, "message": "Unauthorized access"},
                status_code=403
            )

        data = await request.json()
        payment_id = int(data.get("id")) if data.get("id") else None
        reason = str(data.get("reason", None)) if data.get("reason") else None

        if not payment_id:
            return JSONResponse(
                content={"success": False, "message": "Invalid payment ID"},
                status_code=400
            )

        payment = await payments.get(id=payment_id)
        if not payment:
            return JSONResponse(
                content={"success": False, "message": "Payment not found"},
                status_code=404
            )

        updated_payment = await payments.update(
            {'id': payment_id},
            status="canceled",
            updated_by=f"#{user_data.get('id')}-{user_data.get('username')}",
            updated_at=datetime.datetime.now(datetime.timezone.utc),
            note=reason
        )

        if not updated_payment:
            return JSONResponse(
                content={"success": False, "message": "Failed to update payment"},
                status_code=500
            )

        logger.debug(f"Payment canceled: {updated_payment}")
        return JSONResponse(
            content={"success": True, "message": "Payment canceled successfully", 'id': payment_id},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error canceling payment: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "error": str(e)}
        )




@router.post("/api/accept-payment", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def accept_payment(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(
                content={"success": False, "message": "Unauthorized"},
                status_code=401
            )
        if not user_data.get("is_admin", False):
            return JSONResponse(
                content={"success": False, "message": "Unauthorized access"},
                status_code=403
            )

        data = await request.json()
        # {payment_id: "5", extension_months: 1, balance_to_add: null}
        payment_id = int(data.get("payment_id")) if data.get("payment_id") else None
        extension_months_raw = int(data.get("extension_months")) if data.get("extension_months") else 0
        balance_to_add = float(data.get("balance_to_add")) if data.get("balance_to_add") else 0

        if not payment_id:
            return JSONResponse(
                content={"success": False, "message": "Invalid payment ID"},
                status_code=400
            )
        if extension_months_raw <= 0 or balance_to_add < 0:
            return JSONResponse(
                content={"success": False, "message": "Invalid extension months or balance to add"},
                status_code=400
            )

        payment = await payments.get(id=payment_id)
        if not payment:
            return JSONResponse(
                content={"success": False, "message": "Payment not found"},
                status_code=404
            )
        

        

        target_user = await users.get(id=payment.get("user_id"))
        if not target_user:
            return JSONResponse(
                content={"success": False, "message": "User not found"},
                status_code=404
            )
        

        update_perams = {}

        extension_months = relativedelta(months=extension_months_raw) if extension_months_raw > 0 else relativedelta(months=0)

        if not target_user.get('membership_active'):
            update_perams['membership_active'] = True

            if not target_user.get('membership_start_date'):
                update_perams['membership_start_date'] = datetime.datetime.now(datetime.timezone.utc)

            update_perams['membership_end_date'] = datetime.datetime.now(datetime.timezone.utc) + extension_months
            update_perams['membership_type'] = 'basic'
            if not target_user.get('membership_renewal_date'):
                update_perams['membership_renewal_date'] = datetime.datetime.now(datetime.timezone.utc) + extension_months - datetime.timedelta(days=5)
            else:
                update_perams['membership_renewal_date'] = target_user.get('membership_renewal_date') + extension_months
        else:
            update_perams['membership_end_date'] = target_user.get('membership_end_date', datetime.datetime.now(datetime.timezone.utc)) + extension_months
            if not target_user.get('membership_renewal_date'):
                update_perams['membership_renewal_date'] = datetime.datetime.now(datetime.timezone.utc) + extension_months - datetime.timedelta(days=5)
            else:
                update_perams['membership_renewal_date'] = target_user.get('membership_renewal_date') + extension_months

        update_perams['membership_renewal_by'] = f"#{user_data.get('id')}-{user_data.get('username')}"

        if target_user.get('membership_cancelled'):
            update_perams['membership_cancelled'] = False
            update_perams['membership_cancelled_reason'] = None
            update_perams['membership_cancelled_at'] = None
            update_perams['membership_cancelled_by'] = None

        if balance_to_add > 0:
            update_perams['balance'] = target_user.get('balance', 0.0) + balance_to_add
        
        # if old_renewal_date do like this take the month like "Subscription Extended to jan, feb"
        

        user_subscription_updated = await users.update(
            {'id': payment.get("user_id")},
            **update_perams,
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        ) 
        if not user_subscription_updated:
            return JSONResponse(
                content={"success": False, "message": "Failed to update user subscription"},
                status_code=500
            )


        payment_note = f"Subscription Extended to {update_perams.get('membership_end_date').strftime('%b %Y')} ({extension_months_raw} months)"

        updated_payment = await payments.update(
            {'id': payment_id},
            status="completed",
            note=payment_note,
            updated_by=f"#{user_data.get('id')}-{user_data.get('username')}",
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        

        if not updated_payment:
            return JSONResponse(
                content={"success": False, "message": "Failed to update payment"},
                status_code=500
            )
        
        try:
            asyncio.create_task(
                send_renewal_notification(
                    user_id=target_user.get("id"),
                    months_extended=extension_months_raw,
                    old_end_date=target_user.get('membership_end_date', datetime.datetime.now(datetime.timezone.utc)),
                    new_end_date=update_perams.get('membership_end_date'),
                )
            )
        except Exception as e:
            logger.error(f"Error sending renewal notification: {traceback.format_exc()}")

        logger.debug(f"Payment accepted: {updated_payment}")
        return JSONResponse(
            content={"success": True, "message": "Payment accepted successfully", 'id': payment_id},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error accepting payment: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "error": str(e)}
        )
