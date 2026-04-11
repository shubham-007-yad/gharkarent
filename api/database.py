from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise ValueError("CRITICAL ERROR: MONGODB_URL environment variable is MISSING. Please add it to Vercel Settings.")

DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

async def get_database():
    return db

# Helper for getting specific collections
def get_collection(name: str):
    return db[name]
