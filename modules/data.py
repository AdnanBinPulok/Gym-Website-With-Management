import json
from cachetools import TTLCache

from services.logging import logger
from services.database import users

import datetime
import traceback
import aiohttp
import pytz

from aiocache import cached

cached_site_data = TTLCache(maxsize=1, ttl=5)
async def get_config() -> dict | None:
    """
    Get site configuration data with proper error handling.

    Returns:
        dict | None: Site data if found, None otherwise
    """
    global cached_site_data
    if cached_site_data.get("site_data"):
        return cached_site_data.get("site_data")
    try:
        with open('./data/config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            try:
                data['year'] = datetime.datetime.now(pytz.timezone(data.get("timezone", "UTC"))).year
            except Exception as e:
                data['year'] = datetime.datetime.now(datetime.timezone.utc).year
            cached_site_data["site_data"] = data
            return data
    except Exception as e:
        return None
    

cached_seo_data = TTLCache(maxsize=1, ttl=5)
async def get_seo_page_data() -> dict:
    """
    Get SEO page data from the site configuration.

    Returns:
        dict: SEO data
    """
    try:
        global cached_seo_data
        if cached_seo_data.get("seo_data"):
            return cached_seo_data.get("seo_data")
        with open('./data/seo.json', 'r', encoding='utf-8') as f:
            seo_data = json.load(f)
        cached_seo_data["seo_data"] = seo_data
        return seo_data
    except Exception as e:
        logger.error(f"Error getting SEO page data: {traceback.format_exc()}")
        return {}

async def save_seo_page_data(data: dict) -> bool:
    """
    Save SEO page data to the site configuration.

    Args:
        data (dict): SEO data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open('./data/seo.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        # clear the cache after saving new SEO data
        cached_seo_data.clear()
        return True
    except Exception as e:
        logger.error(f"Error saving SEO page data: {traceback.format_exc()}")
        return False


async def get_timezone() -> pytz.timezone:
    """
    Get the timezone from the site configuration.

    Returns:
        pytz.timezone: Timezone
    """
    try:
        site_data = await get_config()
        return pytz.timezone(site_data.get("timezone", "UTC"))
    except Exception as e:
        logger.error(f"Error getting timezone: {traceback.format_exc()}")
        return pytz.timezone("UTC")


async def save_config(data: dict) -> bool:
    """
    Save site configuration data.

    Args:
        data (dict): Site configuration data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open('./data/config.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {traceback.format_exc()}")
        return False


cached_schedule_data = TTLCache(maxsize=1, ttl=5)
async def get_schedule_data():
    global cached_schedule_data
    if cached_schedule_data.get("schedule"):
        return cached_schedule_data.get("schedule")
    try:
        with open('./data/schedule.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            cached_schedule_data["schedule"] = data
            return data
    except Exception as e:
        return None
    
async def save_schedule_data(data: dict) -> bool:
    """
    Save schedule data.

    Args:
        data (dict): Schedule data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open('./data/schedule.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        cached_schedule_data.clear()  # Clear cache after saving new schedule data
        return True
    except Exception as e:
        logger.error(f"Error saving schedule: {traceback.format_exc()}")
        return False
    
cached_gallery_data = TTLCache(maxsize=1, ttl=5)
async def get_gallery_data():
    global cached_gallery_data
    if cached_gallery_data.get("gallery"):
        return cached_gallery_data.get("gallery")
    try:
        with open('./data/gallery.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            cached_gallery_data["gallery"] = data
            return data
    except Exception as e:
        return None
    
async def save_gallery_data(data: dict) -> bool:
    """
    Save gallery data.

    Args:
        data (dict): Gallery data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open('./data/gallery.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        cached_gallery_data.clear()  # Clear cache after saving new gallery data
        return True
    except Exception as e:
        logger.error(f"Error saving gallery: {traceback.format_exc()}")
        return False

cached_get_subscriptions_plans = TTLCache(maxsize=1, ttl=5)
async def get_subscriptions_plans():
    """
    Get subscription plans from the site configuration.

    Returns:
        dict: Subscription plans data
    """
    global cached_get_subscriptions_plans
    if cached_get_subscriptions_plans.get("subscriptions_plans"):
        return cached_get_subscriptions_plans.get("subscriptions_plans")
    try:
        with open('./data/subscriptions_plans.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            cached_get_subscriptions_plans["subscriptions_plans"] = data
            return data
    except Exception as e:
        logger.error(f"Error getting subscriptions plans: {traceback.format_exc()}")
        return None

async def save_subscriptions_plans(data: dict) -> bool:
    """
    Save subscription plans to the site configuration.

    Args:
        data (dict): Subscription plans data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open('./data/subscriptions_plans.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        cached_get_subscriptions_plans.clear()  # Clear cache after saving new subscription plans
        return True
    except Exception as e:
        logger.error(f"Error saving subscriptions plans: {traceback.format_exc()}")
        return False
    

cached_get_payment_methods = TTLCache(maxsize=1, ttl=5)
async def get_payment_methods():
    """
    Get payment methods from the site configuration.

    Returns:
        dict: Payment methods data
    """
    global cached_get_payment_methods
    if cached_get_payment_methods.get("payment_methods"):
        return cached_get_payment_methods.get("payment_methods")
    try:
        with open('./data/payment_methods.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            cached_get_payment_methods["payment_methods"] = data
            return data
    except Exception as e:
        logger.error(f"Error getting payment methods: {traceback.format_exc()}")
        return None
    
async def save_payment_methods(data: dict) -> bool:
    """
    Save payment methods to the site configuration.

    Args:
        data (dict): Payment methods data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open('./data/payment_methods.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        cached_get_payment_methods.clear()  # Clear cache after saving new payment methods
        return True
    except Exception as e:
        logger.error(f"Error saving payment methods: {traceback.format_exc()}")
        return False
