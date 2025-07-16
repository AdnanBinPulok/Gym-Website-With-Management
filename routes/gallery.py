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


from modules.data import get_config,get_timezone,get_gallery_data,save_gallery_data
from modules.functions import fetch_user_data,generate_session_id
from modules.storage import upload_file, delete_image
import asyncio

from modules.rate_limiter import RateLimiter

import aiohttp




router = APIRouter()
templates = Jinja2Templates(directory="static")


rate_limiter = RateLimiter(times=30, seconds=5)


#/api/get-gallery
@router.get("/api/get-gallery", response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def get_gallery(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        if not user_data.get('is_admin', False):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        raw_gallery_data = await get_gallery_data()

        gallery_data = [{'url': item, 'type': 'image'} for item in raw_gallery_data]

        return JSONResponse(status_code=200, content={"success": True, "data":gallery_data})

    except Exception as e:
        logger.error(f"Error in get_gallery: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


@router.post('/api/upload-new-image-to-gallery', response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def upload_new_image_to_gallery(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        if not user_data.get('is_admin', False):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        form = await request.form()
        image = form.get('image')

        gallery_raw_data = await get_gallery_data()

        if len(gallery_raw_data) >= 30:
            logger.error("Gallery is full, cannot upload new image")
            return JSONResponse(status_code=400, content={"error": "Gallery is full, cannot upload new image"})

        file_uploaded_data = await upload_file(image.file)

        if not file_uploaded_data:
            logger.error("Failed to upload file: No data returned")
            return JSONResponse(status_code=500, content={"error": "Failed to upload file"})
        
        if not file_uploaded_data.get('success', False):
            logger.error(f"Failed to upload file: {file_uploaded_data.get('message', 'Unknown error')}")
            return JSONResponse(status_code=500, content={"error": "Failed to upload file"})
        
        gallery_raw_data = await get_gallery_data()
        gallery_raw_data.append(file_uploaded_data.get('file_url'))
        await save_gallery_data(gallery_raw_data)

        return JSONResponse(status_code=200, content={"success": True, "file_url": file_uploaded_data.get('file_url'), "download_url": file_uploaded_data.get('download_url')})
    except Exception as e:
        logger.error(f"Error in upload_new_image_to_gallery: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


@router.post('/api/delete-gallery-item', response_class=JSONResponse, dependencies=[Depends(rate_limiter)])
async def delete_gallery_item(request: Request):
    try:
        user_data = await fetch_user_data(request)
        if not user_data:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        if not user_data.get('is_admin', False):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        data = await request.json()
        image_url = data.get('url')

        if not image_url:
            return JSONResponse(status_code=400, content={"error": "No image URL provided"})

        gallery_raw_data = await get_gallery_data()
        if image_url not in gallery_raw_data:
            return JSONResponse(status_code=404, content={"error": "Image not found in gallery"})
        # gallery_raw_data is a list, so we can remove the image URL directly
        gallery_raw_data.remove(image_url)
        await save_gallery_data(gallery_raw_data)

        return JSONResponse(status_code=200, content={"success": True})

    except Exception as e:
        logger.error(f"Error in delete_gallery_item: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})