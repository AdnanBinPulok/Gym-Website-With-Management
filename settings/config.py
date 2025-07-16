import dotenv
import os

dotenv.load_dotenv(override=True,dotenv_path="./secrets/.env")


class ApiConfig:
    API_HOST = os.getenv("API_HOST")
    API_PORT = int(os.getenv("API_PORT")) if os.getenv("API_PORT") else None
    BASE_URL = os.getenv("BASE_URL")

class ApiInfo:
    NAME = "Fitness Gym"
    DEVICE_ID = "fitnessgym"
    VERSION = "2.0.0"
    DESCRIPTION = "Fitness Gym Website created by @github.com/adnanbinpulok"
    STATUS = "debug" # or live

class DatabaseConfig:
    HOST = os.getenv("DATABASE_HOST")
    PORT = int(os.getenv("DATABASE_PORT")) if os.getenv("DATABASE_PORT") else None
    USER = os.getenv("DATABASE_USER")
    PASSWORD = os.getenv("DATABASE_PASSWORD")
    DATABASE = os.getenv("DATABASE_NAME")
    POOL = int(os.getenv("DATABASE_POOL")) if os.getenv("DATABASE_POOL") else None

class Apis:
    pass

class StorageConfig:
    IMAGE_UPLOAD_SERVER_URL = os.getenv("IMAGE_UPLOAD_SERVER_URL")
    IMAGE_UPLOAD_SERVER_KEY = os.getenv("IMAGE_UPLOAD_SERVER_KEY")
    TIMEOUT = int(os.getenv("TIMEOUT")) if os.getenv("TIMEOUT") else None

class EmailConfig:
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else None
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
