import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check():
    load_dotenv()
    client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    db = client[os.getenv("DATABASE_NAME", "house_db")]
    users = await db.users.find().to_list(10)
    print("Usernames found:", [u["username"] for u in users])
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
