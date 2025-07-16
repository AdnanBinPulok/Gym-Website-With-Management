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
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)


from modules.functions import hash_password, check_password

from aiocache import cached

@cached(ttl=None)
async def get_country_flag_url(country_code: str):
    """Get the URL of the country flag emoji based on the country code. Verify if the country code is valid."""
    if not country_code:
        return None
    
    url = f"https://flagcdn.com/256x192/{country_code.lower()}.png"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return url
                else:
                    return None
    except Exception as e:
        logger.error(f"Error fetching country flag URL: {traceback.format_exc()}")
        return None


async def fetch_session_location(session_id: int):
    try:
        session_data = await sessions.get(id=session_id)
        if not session_data:
            return None
        
        ip = session_data.get("ip")
        if not ip:
            return None
        
        # Use a third-party service to get location data from IP
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipinfo.io/{ip}/json") as response:
                if response.status == 200:
                    location_data = await response.json()
                    return location_data
                else:
                    return None
    except Exception as e:
        logger.error(f"Error fetching session location: {traceback.format_exc()}")
        return None

async def set_session_location(session_id: int):
    """Set the location data for a session based on the IP address."""
    try:
        location_data = await fetch_session_location(session_id)
        if not location_data:
            return
        
        logger.debug(f"Location data for session {session_id}: {location_data}")

        country_code = location_data.get("country")
        if not country_code:
            return
        
        country_flag_url = await get_country_flag_url(country_code)
        
        # Update the session with the location data
        updated = await sessions.update(
            {"id": session_id},
            country=location_data.get("country"),
            country_flag=country_flag_url,
            country_code=country_code,
            location=location_data.get("city", "Unknown"),
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        if not updated:
            logger.error(f"Failed to update session {session_id} with location data")
            return
        logger.success(f"Session {session_id} updated with location data: {location_data}")
        return updated
    except Exception as e:
        logger.error(f"Error setting session location: {traceback.format_exc()}")

async def assign_session(user_id,client_ip,remember=False,raw=False):
        new_session_id = await generate_session_id()
        session_data = await sessions.insert(
            session_token=new_session_id,
            user_id=user_id,
            ip=client_ip,
            expires_at=(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)) if remember else (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)),
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        try:
            asyncio.create_task(set_session_location(session_data.get("id")))
        except Exception as e:
            logger.error(f"Error fetching session location: {traceback.format_exc()}")
        
        try:
            last_login_updated = await users.update(
                {"id": user_id},
                last_login=datetime.datetime.now(datetime.timezone.utc)
            )
            if not last_login_updated:
                logger.error(f"Failed to update last login for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {traceback.format_exc()}")

        if not raw:
            response = JSONResponse(content={"success": True}, status_code=200)
            response.set_cookie("session_token", new_session_id, httponly=True, samesite="strict",expires=None)
            return response
        else:
            return {
                "success": True,
                "session_token": new_session_id,
                "expires_at": session_data.get("expires_at")
            }

@router.post("/api/login", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def login_route(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if user_data:
            return JSONResponse(status_code=400, content={"error": "You are already logged in"})
        
        data = await request.json()
        logger.debug(f"Login data: {data}")

        email = data.get("email")
        password = data.get("password")
        remember = data.get("remember", False)
        if not email or not password:
            return JSONResponse(status_code=400, content={"error": "Missing required fields"})
        
        if not isinstance(remember, bool):
            return JSONResponse(status_code=400, content={"error": "Invalid remember value"})
        
        target_user_data = await users.get(email=email)
        if not target_user_data:
            return JSONResponse(status_code=400, content={"error": "Invalid email"})
        

        if target_user_data.get('password'):
            if not await check_password(password, target_user_data.get("password")):
                return JSONResponse(status_code=400, content={"error": "Invalid email or password"})
        else:
            try:
                password_added = await users.update(
                    {"id": target_user_data.get("id")},
                    password=await hash_password(password),
                    updated_at=datetime.datetime.now(datetime.timezone.utc)
                )
                if not password_added:
                    logger.warning(f"Failed to add password for user first login {target_user_data.get('id')}")
            except Exception as e:
                logger.error(f"Error adding password for user first login {target_user_data.get('id')}: {traceback.format_exc()}")

        return await assign_session(target_user_data.get("id"), request.client.host, remember=remember)
    except Exception as e:
        logger.error(f"Error logging in: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/logout", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def logout_route(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=400, content={"error": "You are not logged in"})

        await sessions.delete(session_token=request.cookies.get("session_token"))
        response = JSONResponse(content={"success": True}, status_code=200)
        response.delete_cookie("session_token")
        return response
    except Exception as e:
        logger.error(f"Error logging out: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


already_sended_password_reset = TTLCache(maxsize=1000, ttl=3600)  # Cache for 1 hour
RESET_LINK_PER_EMAIL = 3 # Limit to 1 reset link per email per hour

async def is_reset_link_allowed(email: str) -> bool:
    """Check if a reset link can be sent to the email."""
    if email in already_sended_password_reset:
        if already_sended_password_reset[email] >= RESET_LINK_PER_EMAIL:
            return False
    if email not in already_sended_password_reset:
        already_sended_password_reset[email] = 0
    already_sended_password_reset[email] += 1
    return True


@router.post("/api/forgot-password", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def forgot_password_route(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        if not email:
            return JSONResponse(status_code=400, content={"error": "Email is required"})

        user_data = await users.get(email=email)
        if not user_data:
            return JSONResponse(status_code=400, content={"error": "User not found"})
        
        if not await is_reset_link_allowed(email):
            return JSONResponse(status_code=429, content={"error": "Too many password reset requests. Please try again later."})

        # Here you would typically send an email with a password reset link
        # For this example, we will just log the action
        logger.info(f"Password reset requested for user {user_data.get('id')} ({email})")

        return JSONResponse(content={"success": True}, status_code=200)
    except Exception as e:
        logger.error(f"Error processing forgot password request: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/change-password", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def change_password_route(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=400, content={"error": "You are not logged in"})
        data = await request.json()
        logger.debug(f"Change password data: {data}")

        current_password = data.get("current_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        if not current_password or not new_password or not confirm_password:
            return JSONResponse(status_code=400, content={"error": "Missing required fields"})
        
        if new_password != confirm_password:
            return JSONResponse(status_code=400, content={"error": "New password and confirm password do not match"})
        
        print(f"Current password: {current_password}, New password: {new_password}, Confirm password: {confirm_password}")
        
        user_data = await users.get(id=user_data.get("id"))
        if not user_data:
            return JSONResponse(status_code=400, content={"error": "User not found"})
        if not await check_password(current_password, user_data.get("password")):
            return JSONResponse(status_code=400, content={"error": "Current password is incorrect"})
        
        hashed_new_password = await hash_password(new_password)
        updated = await users.update(
            {"id": user_data.get("id")},
            password=hashed_new_password,
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        if not updated:
            return JSONResponse(status_code=500, content={"error": "Failed to update password"})
        
        # delete the session to force re-login
        await sessions.delete(user_id=user_data.get("id"))
        # assign a new session
        assigned_cookie_data = await assign_session(user_data.get("id"), request.client.host, remember=True, raw=True)
        new_cookie = assigned_cookie_data.get("session_token")
        response = JSONResponse(content={"success": True}, status_code=200)
        response.set_cookie("session_token", new_cookie, httponly=True, samesite="strict", expires=None)
        return response
    except Exception as e:
        logger.error(f"Error processing change password request: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")