import asyncio
import os
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Path handling for both local and Vercel structures
load_dotenv()

def get_password_hash(password: str):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

async def force_update_admin():
    MONGODB_URL = os.getenv("MONGODB_URL")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")
    
    print(f"Connecting to Database...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    new_password = "Admin@007"
    hashed = get_password_hash(new_password)
    
    print(f"Updating 'admin' user password...")
    result = await db.users.update_one(
        {"username": "admin"},
        {"$set": {"hashed_password": hashed}},
        upsert=True
    )
    
    if result.modified_count > 0:
        print("✅ SUCCESS: Admin password updated to Admin@007")
    elif result.upserted_id:
        print("✅ SUCCESS: Admin user created with password Admin@007")
    else:
        print("ℹ️  Note: User already had this password or no change made.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(force_update_admin())
