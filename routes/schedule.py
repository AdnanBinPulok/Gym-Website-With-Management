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


from modules.data import get_config,get_timezone,get_gallery_data,save_gallery_data,get_schedule_data,save_schedule_data
from modules.functions import fetch_user_data,generate_session_id
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)



# {
#     "monday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": true
#         }
#     ],
#     "tuesday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": true
#         }
#     ],
#     "wednesday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": true
#         }
#     ],
#     "thursday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": true
#         }
#     ],
#     "friday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": false
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": false
#         }
#     ],
#     "saturday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": true
#         }
#     ],
#     "sunday": [
#         {
#             "gender": "male",
#             "start_time": "7:00 AM",
#             "end_time": "12:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "female",
#             "start_time": "12:00 PM",
#             "end_time": "5:00 PM",
#             "is_open": true
#         },
#         {
#             "gender": "all",
#             "start_time": "5:00 PM",
#             "end_time": "11:00 PM",
#             "is_open": true
#         }
#     ]
# }

def verify_schedule_data_schema(data):
    import re

    # Helper to validate time format (e.g., "7:00 AM", "12:30 PM")
    def is_valid_time_format(time_str):
        return bool(re.match(r"^(1[0-2]|0?[1-9]):[0-5][0-9]\s?(AM|PM)$", time_str))

    if not isinstance(data, dict):
        return False

    valid_days = [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ]

    valid_genders = {"male", "female", "all"}

    for day, slots in data.items():
        if day not in valid_days:
            return False
        if not isinstance(slots, list):
            return False

        for slot in slots:
            if not isinstance(slot, dict):
                return False

            if "gender" not in slot or "start_time" not in slot or "end_time" not in slot or "is_open" not in slot:
                return False

            if slot["gender"] not in valid_genders:
                return False
            if not isinstance(slot["is_open"], bool):
                return False
            if not is_valid_time_format(slot["start_time"]):
                return False
            if not is_valid_time_format(slot["end_time"]):
                return False

    return True


@router.get("/api/get-schedule", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_schedule(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        if not user_data.get('is_trainer', False):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        raw_schedule_data = await get_schedule_data()

        return JSONResponse(status_code=200, content={"success": True, "data": raw_schedule_data})

    except Exception as e:
        logger.error(f"Error in get_schedule: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})
    
@router.post("/api/save-schedule", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def save_schedule(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        if not user_data.get('is_admin', False):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        data = await request.json()

        if not verify_schedule_data_schema(data):
            return JSONResponse(status_code=400, content={"error": "Invalid schedule data format"})

        await save_schedule_data(data)

        return JSONResponse(status_code=200, content={"success": True})

    except Exception as e:
        logger.error(f"Error in save_schedule: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})