import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def inspect_all_data():
    MONGODB_URL = os.getenv("MONGODB_URL")
    DATABASE_NAME = "house_db"
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    tenants = await db.tenants.find().to_list(100)
    print("--- 2026 DATA INSPECTION ---")
    for t in tenants:
        t_id = str(t["_id"])
        payments = await db.payments.find({"tenant_id": t_id, "year": 2026}).sort([("month", 1)]).to_list(100)
        
        if not payments:
            continue
            
        print(f"\nTenant: {t['name']} (Room: {t.get('room_number')}, Rent: {t.get('rent_amount')})")
        for p in payments:
            print(f"  [{p['month']} {p['year']}] Submitted: ₹{p['amount']} | Elec: ₹{p['electricity_amount']} | Pending: ₹{p.get('pending_amount')} | Status: {p['status']}")

    client.close()

if __name__ == "__main__":
    asyncio.run(inspect_all_data())
