from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")

db_error = None
client = None
db = None

if not MONGODB_URL:
    db_error = "MONGODB_URL is missing from environment variables"
else:
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
    except Exception as e:
        db_error = f"Connection error: {str(e)}"

async def get_database():
    if db_error:
        raise HTTPException(status_code=500, detail=f"Database Configuration Error: {db_error}")
    return db

# Helper for getting specific collections
def get_collection(name: str):
    return db[name]
