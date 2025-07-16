import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from fastapi import Request
import uvicorn
from fastapi.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles

from services.logging import logger
import traceback
import os

from services.database import users

from settings.config import ApiInfo,ApiConfig
from modules.data import get_config

from modules.functions import hash_password, check_password

templates = Jinja2Templates(directory="static")

class CustomFastAPI(FastAPI):
    def __init__(self):
        super().__init__(
            title=ApiInfo.NAME,
            version=ApiInfo.VERSION,
            description=ApiInfo.DESCRIPTION,
            docs_url=None,
            redoc_url=None
        )


app = CustomFastAPI()



app.mount("/static", StaticFiles(directory="./static"), name="static")
app.mount("/images", StaticFiles(directory="./data/images"), name="images")


async def create_superuser():
    config_data = await get_config()

    superadmin = config_data.get("superadmin", {})
    superadmin_email = superadmin.get("email", "admin@example.com")
    superadmin_username = 'admin'
    superadmin_password = superadmin.get("password", "admin123")

    user_exists = await users.get(email=superadmin_email)
    if user_exists:
        logger.info(f"Superuser with email {superadmin_email} already exists.")
        return
    
    users_inserted = await users.insert(
        username=superadmin_username,
        full_name="Super Admin",
        email=superadmin_email,
        role="superadmin",
        password=await hash_password(superadmin_password),
    )
    if users_inserted:
        logger.success(f"Superuser created with email {superadmin_email}.")
    else:
        logger.error(f"Failed to create superuser with email {superadmin_email}.")

async def initialize_routes():
    # Add all routers here from ./routes folder
    for file in os.listdir("./routes"):
        if file.endswith(".py"):
            module = file[:-3]
            if module != "__init__":
                module_router = __import__(f"routes.{module}", fromlist=["router"])
                app.include_router(module_router.router)
                logger.info(f"Router {module} included ✅")
                


async def initialize_pages():
    # Add all routers here from ./pages folder
    for file in os.listdir("./pages"):
        if file.endswith(".py"):
            module = file[:-3]
            if module != "__init__":
                module_router = __import__(f"pages.{module}", fromlist=["router"])
                app.include_router(module_router.router)
                logger.info(f"Router {module} included ✅")
                

# Custom 404 handler for route not found
@app.exception_handler(404)
async def route_not_found_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        return JSONResponse(content={"error": "Route not found"}, status_code=404)
    return templates.TemplateResponse("/errors/404.html", {"request": request}, status_code=404)

# General HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # if the status code is 429, return 429.html
    if exc.status_code == 429:
        return templates.TemplateResponse("/errors/429.html", {"request": request}, status_code=429)
    if request.url.path.startswith("/api"):
        return JSONResponse(content={"error": exc.detail}, status_code=exc.status_code)
    return templates.TemplateResponse("/errors/500.html", {"request": request}, status_code=500)


async def main():
    try:
        from services.database import InitDatabase
        await InitDatabase()
        await initialize_routes()
        await initialize_pages()

        await create_superuser()
        
        tasks = []

        async def start_api():
            try:
                api_config = uvicorn.Config(
                    app,
                    host=ApiConfig.API_HOST,
                    port=ApiConfig.API_PORT,
                    reload=True
                )
                server = uvicorn.Server(api_config)
                await server.serve()
            except Exception as e:
                logger.error(f"Error in file {__file__}: {traceback.format_exc()}")
        try:
            tasks.append(asyncio.create_task(start_api()))
        except Exception as e:
            logger.error(f"Error in file {__file__}: {traceback.format_exc()}")

        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error in file {__file__}: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())