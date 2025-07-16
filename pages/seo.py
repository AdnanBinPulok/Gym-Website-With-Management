from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi import HTTPException
import traceback
from fastapi import Depends

router = APIRouter()
templates = Jinja2Templates(directory="static")

from services.logging import logger
from modules.data import get_config
from modules.functions import fetch_user_data
from modules.rate_limiter import RateLimiter

from typing import List
rate_limiter = RateLimiter(times=30, seconds=5)


from aiocache import cached

def generate_sitemap_entry(loc: str, changefreq: str, priority: str) -> str:
    return f"""
    <url>
        <loc>{loc}</loc>
        <changefreq>{changefreq}</changefreq>
        <priority>{priority}</priority>
    </url>
    """


@cached(ttl=3600)
async def generate_sitemap(urls: List[dict]) -> str:
    entries = [generate_sitemap_entry(url['loc'], url['changefreq'], url['priority']) for url in urls]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {''.join(entries)}
</urlset>
"""

@cached(ttl=3600)
async def generate_robots_txt() -> str:
    config_data = await get_config()
    domain = config_data.get('domain', 'example.com')
    return f"""User-agent: *
Disallow: /api
Disallow: /dashboard

Allow: /
Allow: /login
Allow: /pricing
Allow: /gallery
Allow: /schedule
Allow: /contacts
Allow: /about
Allow: /policy

Sitemap: https://{domain}/sitemap.xml
"""

@router.get("/robots.txt", response_class=PlainTextResponse, dependencies=[Depends(rate_limiter)])
async def robots(request: Request):
    return PlainTextResponse(content=await generate_robots_txt(),status_code=200, media_type="text/plain")

@router.get("/sitemap.xml", response_class=HTMLResponse, dependencies=[Depends(rate_limiter)])
async def sitemap(request: Request):
    try:
        config_data = await get_config()
        domain = config_data.get('domain', '')

        urls = [
            {"loc": f"https://{domain}/",  "changefreq": "daily", "priority": "1.0"},
            {"loc": f"https://{domain}/login",  "changefreq": "monthly", "priority": "0.9"},
            {"loc": f"https://{domain}/pricing",  "changefreq": "monthly", "priority": "0.9"},
            {"loc": f"https://{domain}/gallery",  "changefreq": "monthly", "priority": "0.9"},
            {"loc": f"https://{domain}/schedule",  "changefreq": "monthly", "priority": "0.9"},
            {"loc": f"https://{domain}/contact",  "changefreq": "monthly", "priority": "0.8"},
            {"loc": f"https://{domain}/policy",  "changefreq": "monthly", "priority": "0.8"},
            {"loc": f"https://{domain}/about",  "changefreq": "monthly", "priority": "0.8"},
        ]

        sitemap_xml = await generate_sitemap(urls)
        return HTMLResponse(content=sitemap_xml, media_type="application/xml")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error while generating sitemap",
            headers={"X-Error": "Sitemap generation failed"}
        )