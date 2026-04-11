from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    print("CRITICAL: MONGODB_URL is not set in environment variables!")

DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")

try:
    client = AsyncIOMotorClient(MONGODB_URL) if MONGODB_URL else None
    db = client[DATABASE_NAME] if client else None
except Exception as e:
    print(f"Error initializing MongoDB client: {e}")
    client = None
    db = None

async def get_database():
    return db

# Helper for getting specific collections
def get_collection(name: str):
    return db[name]
