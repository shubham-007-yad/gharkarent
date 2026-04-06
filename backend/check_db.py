import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check():
    MONGODB_URL = os.getenv("MONGODB_URL")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")
    print(f"Connecting to: {MONGODB_URL.split('@')[-1]}...") # Safe print
    
    try:
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        user = await db.users.find_one({"username": "admin"})
        if user:
            print(f"✅ User 'admin' exists in database.")
        else:
            print(f"❌ User 'admin' NOT found. Run 'python create_admin.py' now.")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
