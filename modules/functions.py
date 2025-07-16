from services.database import users, sessions
from fastapi import Request, Depends
import random
import string
import datetime
import traceback
from services.logging import logger

import pytz

from modules.data import get_timezone
from modules.mail import generate_renewal_email, send_mail
from settings.config import EmailConfig

from modules.data import get_config

from passlib.hash import pbkdf2_sha256


async def fetch_user_data(request: Request):
    try:
        session_token = request.cookies.get("session_token")
        if not session_token:
            return None
        
        logger.debug(f"Fetching user data for session token: {session_token}")
        
        session_data = await sessions.get(session_token=session_token)
        if not session_data:
            logger.warning(f"No session data found for token: {session_token}")
            return None
        
        if session_data.get("expires_at"):
            current_datetime = datetime.datetime.now(datetime.timezone.utc)
            expires_at = session_data.get("expires_at")
            if current_datetime > expires_at:
                logger.warning(f"Session expired for token: {session_token}")
                return None

        user_data = await users.get(id=session_data.get("user_id"))
        if not user_data:
            logger.warning(f"No user data found for user ID: {session_data.get('user_id')}")
            return None
        
        modified_user_data = {}

        local_tz = await get_timezone()

        for key, value in user_data.items():
            if key == "password":
                continue
            
            if isinstance(value, datetime.datetime):
                modified_user_data[key] = value.astimezone(local_tz).isoformat()
            else:
                modified_user_data[key] = value
        logger.success(f"User data fetched successfully for user ID: {user_data.get('user_id')}")


        modified_user_data['is_admin'] = modified_user_data.get('role') in ['admin', 'superadmin']
        modified_user_data['is_trainer'] = modified_user_data.get('role') in ['trainer', 'admin', 'superadmin']
        return modified_user_data
    except Exception as e:
        print(f"Error fetching user data: {traceback.format_exc()}")
        return None


async def get_stats_data() -> dict:
    data = {
        "total_members": 103,
        "total_trainer": 1,
        "success_rate": 98,
        "total_workout_days": 6,
        "daily_operation_hours": 16,
        "open_stats": {
            "days": "Everyday",
            "hours": "7:00 AM - 11:00 PM",
        }
    }
    return data


async def generate_session_id(length: int=32) -> str:
    """Generate a unique session ID."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))



async def send_renewal_notification(
    user_id: int,
    months_extended: int,
    old_end_date: datetime.datetime,
    new_end_date: datetime.datetime
):
    try:
        user = await users.get(id=user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found for renewal notification")
            return
        
        generated_mail = await generate_renewal_email(
            full_name=user.get("full_name", "User"),
            username=user.get("username", "user"),
            email=user.get("email", "user@example.com"),
            months_extended=months_extended,
            old_end_date=old_end_date,
            new_end_date=new_end_date
        )

        if not generated_mail:
            logger.error(f"Failed to generate renewal email for user {user.get('username')}")
            return
        
        config_data = await get_config()

        site_name = config_data.get('name')

        subject = f"{site_name} - Verify Your Email"
        sender = EmailConfig.SMTP_USER
        recipients = [user.get("email")]
        attachments = None
        type = "html"

        await send_mail(
            text=generated_mail,
            type=type,
            subject=subject,
            sender=sender,
            recipients=recipients,
            attachments=attachments
        )

    except Exception as e:
        logger.error(f"Error sending renewal notification: {traceback.format_exc()}")


async def hash_password(password: str) -> str:
    # Hash the password using passlib's pbkdf2_sha256
    return pbkdf2_sha256.hash(password)

async def check_password(password: str, hashed_password: str) -> bool:
    # Verify the password using passlib's bcrypt
    return pbkdf2_sha256.verify(password, hashed_password)
