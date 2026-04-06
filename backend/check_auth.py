import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import pymongo

load_dotenv()

async def test_all_credentials():
    URL = os.getenv("MONGODB_URL")
    DB_NAME = os.getenv("DATABASE_NAME", "house_db")
    
    print("
--- 🔍 DIAGNOSTIC TOOL ---")
    
    # 1. Test Network
    print(f"1. Testing network connection to cluster...")
    try:
        client = AsyncIOMotorClient(URL, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        print("   ✅ Network connection OK!")
    except pymongo.errors.OperationFailure as e:
        if "Authentication failed" in str(e) or "bad auth" in str(e):
            print("   ❌ AUTHENTICATION FAILED!")
            print("   The username 'house' or the password '[REDACTED]' is wrong.")
            print("   Go to Atlas -> Database Access and reset the password for 'house' to '[REDACTED]'.")
        else:
            print(f"   ❌ ERROR: {e}")
        return
    except Exception as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        print("   Is your IP whitelisted in Atlas? (Try 0.0.0.0/0)")
        return

    # 2. Check Database Access
    try:
        db = client[DB_NAME]
        collections = await db.list_collection_names()
        print(f"2. Database access OK! Collections found: {collections}")
        
        # 3. Check for Admin
        admin = await db.users.find_one({"username": "admin"})
        if admin:
            print("   ✅ Admin user exists. You can log in!")
        else:
            print("   ⚠️ Admin user NOT found. Run 'python seed_data.py' now.")
            
    except Exception as e:
        print(f"   ❌ DB ACCESS ERROR: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_all_credentials())
