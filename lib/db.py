from enum import Enum
from models.settings import Settings
import motor.motor_asyncio

settings = Settings()


class Collections(str, Enum):
    users = "users"
    posts = "posts"
    comments = "comments"
    tokens = "tokens"
    likes = "likes"
    sessions = "sessions"
    transfers = "transfers"
    otps = "otps"
    


client = motor.motor_asyncio.AsyncIOMotorClient(settings.db_url)

db = client[settings.db_name]
