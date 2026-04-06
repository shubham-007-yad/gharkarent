import asyncio
import os
import auth
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def create_admin_user(username, password):
    MONGODB_URL = os.getenv("MONGODB_URL")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    # Check if user already exists
    existing_user = await db.users.find_one({"username": username})
    if existing_user:
        print(f"User {username} already exists.")
        return

    hashed_password = auth.get_password_hash(password)
    new_user = {
        "username": username,
        "hashed_password": hashed_password
    }
    
    result = await db.users.insert_one(new_user)
    print(f"Admin user {username} created successfully with ID: {result.inserted_id}")
    client.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user("admin", "admin123"))
