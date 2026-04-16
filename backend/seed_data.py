import asyncio
import os
from datetime import datetime, date, time
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import auth

load_dotenv()

# Helper to get a clean date (00:00:00)
def clean_date(d=None):
    if d is None:
        d = date.today()
    if isinstance(d, datetime):
        d = d.date()
    return datetime.combine(d, time.min)

async def seed_data():
    MONGODB_URL = os.getenv("MONGODB_URL")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "house_db")
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    print("Connecting to MongoDB Atlas...")

    # 1. Create/Update Admin User
    hashed_password = auth.get_password_hash("Admin@007")
    await db.users.update_one(
        {"username": "admin"},
        {"$set": {"username": "admin", "hashed_password": hashed_password}},
        upsert=True
    )
    print("✅ Admin user 'admin' ready.")

    # 2. Add 6 Random Tenants
    tenants_data = [
        {
            "name": "Rahul Sharma",
            "phone": "9876543210",
            "room_number": "A-101",
            "rent_amount": 12000.0,
            "aadhar_number": "1234567890123456",
            "emergency_contact": "9876500001",
            "move_in_date": clean_date(date(2023, 5, 10)),
            "status": "active"
        },
        {
            "name": "Priya Patel",
            "phone": "8877665544",
            "room_number": "B-202",
            "rent_amount": 15500.0,
            "aadhar_number": "9876543210987654",
            "emergency_contact": "9900112233",
            "move_in_date": clean_date(date(2023, 8, 15)),
            "status": "active"
        },
        {
            "name": "Amit Kumar",
            "phone": "7766554433",
            "room_number": "A-105",
            "rent_amount": 10000.0,
            "aadhar_number": "5544332211005544",
            "emergency_contact": "8877441122",
            "move_in_date": clean_date(date(2024, 1, 5)),
            "status": "active"
        },
        {
            "name": "Suresh Raina",
            "phone": "9988776655",
            "room_number": "C-301",
            "rent_amount": 18000.0,
            "aadhar_number": "1122334455661122",
            "emergency_contact": "9988776600",
            "move_in_date": clean_date(date(2023, 12, 1)),
            "status": "active"
        },
        {
            "name": "Vikram Singh",
            "phone": "9123456789",
            "room_number": "B-205",
            "rent_amount": 14000.0,
            "aadhar_number": "4455667788994455",
            "emergency_contact": "9123456700",
            "move_in_date": clean_date(date(2024, 2, 10)),
            "status": "active"
        },
        {
            "name": "Ananya Iyer",
            "phone": "8123456789",
            "room_number": "D-402",
            "rent_amount": 22000.0,
            "aadhar_number": "7788990011227788",
            "emergency_contact": "8123456700",
            "move_in_date": clean_date(date(2024, 3, 1)),
            "status": "leaving"
        }
    ]
    
    await db.tenants.delete_many({})
    tenant_results = await db.tenants.insert_many(tenants_data)
    tenant_ids = tenant_results.inserted_ids
    print(f"✅ Inserted 6 Tenants.")

    # 3. Add Payments
    current_month = date.today().strftime("%B")
    current_year = date.today().year

    payments = [
        {
            "tenant_id": str(tenant_ids[0]),
            "amount": 12000.0,
            "electricity_amount": 540.0,
            "month": current_month,
            "year": current_year,
            "date": clean_date(),
            "status": "paid",
            "method": "Online"
        },
        {
            "tenant_id": str(tenant_ids[1]),
            "amount": 15500.0,
            "electricity_amount": 720.0,
            "month": current_month,
            "year": current_year,
            "date": clean_date(),
            "status": "paid",
            "method": "Cash"
        }
    ]
    await db.payments.delete_many({})
    await db.payments.insert_many(payments)
    print("✅ Inserted Payments.")

    # 4. Add Maintenance Requests
    maintenance = [
        {
            "tenant_id": str(tenant_ids[2]),
            "tenant_name": "Amit Kumar",
            "issue": "Wall seepage in bedroom",
            "priority": "High",
            "status": "pending",
            "created_at": clean_date()
        }
    ]
    await db.maintenance.delete_many({})
    await db.maintenance.insert_many(maintenance)
    print("✅ Inserted Maintenance Requests.")

    # 5. Add Expenses
    expenses = [
        {"title": "Lift Maintenance", "amount": 5000.0, "category": "Repair", "date": clean_date()},
        {"title": "Sweeper Salary", "amount": 1500.0, "category": "Cleaning", "date": clean_date()}
    ]
    await db.expenses.delete_many({})
    await db.expenses.insert_many(expenses)
    print("✅ Inserted Expenses.")

    client.close()
    print("\n🚀 Database Seeding Complete! Refresh your browser now.")

if __name__ == "__main__":
    asyncio.run(seed_data())
