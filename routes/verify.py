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
from services.database import sessions, users, payments, verify_email_codes
import datetime
from passlib.hash import pbkdf2_sha256

from google.oauth2 import id_token as id_token_module
from google.auth.transport import requests

from aiocache import cached


from modules.data import get_config, get_timezone, get_payment_methods
from modules.functions import fetch_user_data,generate_session_id
from modules.storage import upload_file, delete_image

from modules.mail import send_mail, generate_verify_email_html
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp

from settings.config import ApiConfig, EmailConfig




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)


async def send_verify_email(user_data: dict, verify_email_code_data: dict):
    try:
        site_data = await get_config()
        site_name = site_data.get("name")
        verify_email_url = f"{ApiConfig.BASE_URL}/verify-email?code={verify_email_code_data.get('code')}"
        
        html = await generate_verify_email_html(
            user_id=user_data.get("id"),
            fullname=user_data.get("full_name"),
            email=user_data.get("email"),
            verify_url=verify_email_url,
            expired_at=verify_email_code_data.get("expired_at"),
            sitename=site_name
        )
        
        if not html:
            logger.error("Failed to generate HTML for verification email")
            return False
        
        subject = f"{site_name} - Verify Your Email"
        sender = EmailConfig.SMTP_USER
        recipients = [user_data.get("email")]
        attachments = None
        type = "html"
        
        if not await send_mail(
            text=html,
            type=type,
            subject=subject,
            sender=sender,
            recipients=recipients,
            attachments=attachments
        ):
            logger.error("Failed to send verification email")
            return False

        logger.info(f"Verification email sent to {user_data.get('email')}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending verification email: {traceback.format_exc()}")
        return False

def generate_verify_email_code(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def send_email_verification(user_data:dict):
    try:
        verify_email_code = generate_verify_email_code()
        # delete existing verification codes for the user
        await verify_email_codes.delete(user_id=user_data.get("id"))

        # create new verification code entry
        inserted_code = await verify_email_codes.insert(
            user_id=user_data.get("id"),
            code=verify_email_code,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            expired_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=6)
        )
        if not inserted_code:
            logger.error("Failed to insert verification code into database")
            return False
        
        # send verification email
        if not await send_verify_email(user_data, inserted_code):
            logger.error("Failed to send verification email")
            return False
    except Exception as e:
        logger.error(f"Failed to send email verification: {traceback.format_exc()}")



cached_sended_emails = TTLCache(maxsize=1000, ttl=3600)  # Cache for 1 hour
async def is_email_rate_limited(email: str):
    global cached_sended_emails
    email_sended_count = cached_sended_emails.get(email, 0)
    if email_sended_count >= 5:  # Limit to 5 emails per hour
        return True, f"You have reached the limit of 5 email verifications per hour."
    if email not in cached_sended_emails:
        cached_sended_emails[email] = 0
    cached_sended_emails[email] += 1
    return False, None


@router.post("/api/verify-email", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def verify_email(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        email_rate_limited, error_message = await is_email_rate_limited(user_data.get("email"))
        if email_rate_limited:
            return JSONResponse(content={"success": False, "message": error_message}, status_code=429)

        if user_data.get("email_verified"):
            return JSONResponse(content={"success": True, "message": "Email already verified"}, status_code=200)
        
        try:
            asyncio.create_task(
                send_email_verification(user_data)
            )
        except Exception as e:
            logger.error(f"Error sending verification email: {traceback.format_exc()}")

        return JSONResponse(content={"success": True, "message": "Email verified successfully"}, status_code=200)

    except Exception as e:
        logger.error(f"Error verifying email: {traceback.format_exc()}")
        return JSONResponse(content={"success": False, "message": "Internal server error"}, status_code=500)
    


@router.post("/api/verify-email-code", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def verify_email_code(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(content={"success": False, "message": "Unauthorized"}, status_code=401)
        
        data = await request.json()
        code = data.get("code")
        
        if not code:
            return JSONResponse(content={"success": False, "message": "Code is required"}, status_code=400)
        
        verify_email_code_data = await verify_email_codes.get(
            code=code
        )
        
        if not verify_email_code_data:
            return JSONResponse(content={"success": False, "message": "Invalid or expired code"}, status_code=400)

        user = await users.get(
            id=verify_email_code_data.get("user_id")
        )
        if not user:
            return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)

        # Check if the code is expired
        if datetime.datetime.now(datetime.timezone.utc) > verify_email_code_data.get("expired_at"):
            return JSONResponse(content={"success": False, "message": "Code has expired"}, status_code=400)
        
        # Update user's email verification status
        updated = await users.update(
            {'id': user.get("id")},
            email_verified=True,
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        
        if not updated:
            return JSONResponse(content={"success": False, "message": "Failed to update email verification status"}, status_code=500)
        
        # Delete the verification code from the database
        await verify_email_codes.delete(user_id=user.get("id"))

        return JSONResponse(content={"success": True, "message": "Email verified successfully"}, status_code=200)

    except Exception as e:
        logger.error(f"Error verifying email code: {traceback.format_exc()}")
        return JSONResponse(content={"success": False, "message": "Internal server error"}, status_code=500)