import asyncio
import os
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

def get_password_hash(password: str):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

async def main():
    URL = os.getenv("MONGODB_URL")
    DB_NAME = os.getenv("DATABASE_NAME", "house_db")
    
    print("--- DATABASE FIX TOOL ---")
    print(f"1. Testing Connection to Atlas...")
    
    try:
        # Use a short timeout so we don't wait forever if it fails
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        print("✅ Connection Successful!")
        
        db = client[DB_NAME]
        
        print("2. Ensuring Admin User 'admin' exists...")
        hashed = get_password_hash("admin123")
        await db.users.update_one(
            {"username": "admin"},
            {"$set": {"username": "admin", "hashed_password": hashed}},
            upsert=True
        )
        print("✅ Admin user 'admin' is ready (Pass: admin123).")
        
        count = await db.tenants.count_documents({})
        print(f"3. Cloud Status: Found {count} tenants.")

        print("\n🚀 Everything is fixed! Now start your backend and log in.")
        client.close()
        
    except Exception as e:
        print("\n❌ CONNECTION ERROR")
        print(f"Reason: {str(e)}")
        print("\n--- HOW TO FIX ---")
        print("1. Go to MongoDB Atlas Website -> Network Access.")
        print("2. Click 'Add IP Address' -> 'Allow Access from Anywhere'.")
        print("3. Check if your password in .env is correct.")

if __name__ == "__main__":
    asyncio.run(main())
