from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import io
import csv
from fpdf import FPDF
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, date, datetime
from bson import ObjectId
import logging
import os
import shutil
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

import sys
from pathlib import Path

# Add current directory to path for stable imports
current_dir = str(Path(__file__).parent)
if current_dir not in sys.path:
    sys.path.append(current_dir)

import schemas
import auth
from database import get_database

# Cloudinary Configuration
cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

app = FastAPI()
router = APIRouter()

@app.get("/api/health")
async def app_health():
    return {"status": "ok", "source": "app"}

@router.get("/health")
async def router_health():
    return {"status": "ok", "source": "router"}

# Mount uploads directory safely (Vercel is read-only)
try:
    if not os.path.exists("/tmp/uploads"):
        os.makedirs("/tmp/uploads")
    app.mount("/uploads", StaticFiles(directory="/tmp/uploads"), name="uploads")
except Exception as e:
    print(f"Skipping uploads mount: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to ensure CORS headers on 500 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": "*"}
    )

# Helper function to convert dates for MongoDB
def prepare_mongo_data(data: dict):
    new_data = data.copy()
    for key, value in new_data.items():
        if isinstance(value, date):
            new_data[key] = datetime.combine(value, datetime.min.time())
    return new_data

# Authentication Endpoints
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_database)):
    try:
        user = await db.users.find_one({"username": form_data.username})
        if not user or not auth.verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@router.post("/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db = Depends(get_database)):
    db_user = await db.users.find_one({"username": user.username})
    if db_user: raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user_dict = user.dict()
    new_user_dict["hashed_password"] = hashed_password
    del new_user_dict["password"]
    result = await db.users.insert_one(new_user_dict)
    new_user_dict["_id"] = result.inserted_id
    return new_user_dict

@router.post("/tenant", response_model=schemas.Tenant)
async def create_tenant(tenant: schemas.TenantCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        tenant_dict = prepare_mongo_data(tenant.dict())
        result = await db.tenants.insert_one(tenant_dict)
        tenant_dict["_id"] = str(result.inserted_id)
        tenant_dict["payments"] = []
        tenant_dict["documents"] = []
        return tenant_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rental person: {str(e)}")

@router.get("/tenants/export")
async def export_tenants(status: Optional[str] = None, min_rent: Optional[float] = None, max_rent: Optional[float] = None, search: Optional[str] = None, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        query = {}
        if status and status != "All": query["status"] = status
        rent_query = {}
        if min_rent is not None: rent_query["$gte"] = min_rent
        if max_rent is not None: rent_query["$lte"] = max_rent
        if rent_query: query["rent_amount"] = rent_query
        if search:
            query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"room_number": {"$regex": search, "$options": "i"}}, {"phone": {"$regex": search, "$options": "i"}}]
        cursor = db.tenants.find(query)
        tenants = await cursor.to_list(length=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Phone", "Room Number", "Rent Amount", "Move-in Date", "Status", "Aadhar/ID", "Emergency Contact"])
        for t in tenants:
            move_in = t.get("move_in_date")
            if isinstance(move_in, datetime): move_in = move_in.strftime("%Y-%m-%d")
            writer.writerow([t.get("name", ""), t.get("phone", ""), t.get("room_number", ""), t.get("rent_amount", 0), move_in or "", t.get("status", ""), t.get("aadhar_number", ""), t.get("emergency_contact", "")])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=rentals_export_{date.today()}.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate export")

@router.get("/tenant/{tenant_id}/pdf")
async def export_tenant_pdf(tenant_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
        if not tenant: raise HTTPException(status_code=404, detail="Tenant not found")
        payments = await db.payments.find({"tenant_id": tenant_id}).to_list(length=100)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(190, 15, "Tenant Full Record - Housely.io", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(190, 10, "1. Personal Information", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 8, f"Name: {tenant.get('name')}", ln=True)
        pdf.cell(190, 8, f"Phone: {tenant.get('phone')}", ln=True)
        pdf.cell(190, 8, f"Aadhar/ID: {tenant.get('aadhar_number', 'N/A')}", ln=True)
        pdf.ln(10)
        pdf.cell(190, 10, "2. Rental Details", ln=True)
        pdf.cell(190, 8, f"Room: {tenant.get('room_number')}", ln=True)
        pdf.cell(190, 8, f"Rent: Rs. {tenant.get('rent_amount')}", ln=True)
        pdf_bytes = pdf.output(dest='S')
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Tenant_Record.pdf"})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

@router.get("/tenants", response_model=List[schemas.Tenant])
async def read_tenants(skip: int = 0, limit: int = 100, status: Optional[str] = None, min_rent: Optional[float] = None, max_rent: Optional[float] = None, search: Optional[str] = None, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        query = {}
        if status and status != "All": query["status"] = status
        rent_query = {}
        if min_rent is not None: rent_query["$gte"] = min_rent
        if max_rent is not None: rent_query["$lte"] = max_rent
        if rent_query: query["rent_amount"] = rent_query
        if search:
            query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"room_number": {"$regex": search, "$options": "i"}}, {"phone": {"$regex": search, "$options": "i"}}]
        tenants_cursor = db.tenants.find(query).skip(skip).limit(limit)
        tenants = await tenants_cursor.to_list(length=limit)
        for tenant in tenants:
            tenant["_id"] = str(tenant["_id"])
            tenant_id_str = tenant["_id"]
            payments = await db.payments.find({"tenant_id": tenant_id_str}).to_list(length=100)
            for p in payments: p["_id"] = str(p["_id"])
            tenant["payments"] = payments
            documents = await db.documents.find({"tenant_id": tenant_id_str}).to_list(length=100)
            for d in documents: d["_id"] = str(d["_id"])
            tenant["documents"] = documents
        return [schemas.Tenant(**t) for t in tenants]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/tenant/{tenant_id}", response_model=schemas.Tenant)
async def update_tenant(tenant_id: str, tenant_update: schemas.TenantUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    update_data = prepare_mongo_data(tenant_update.dict(exclude_unset=True))
    result = await db.tenants.find_one_and_update({"_id": ObjectId(tenant_id)}, {"$set": update_data}, return_document=True)
    if not result: raise HTTPException(status_code=404, detail="Not found")
    result["_id"] = str(result["_id"])
    return result

@router.post("/payment/{tenant_id}", response_model=schemas.Payment)
async def create_payment(tenant_id: str, payment: schemas.PaymentCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    p_dict = prepare_mongo_data(payment.dict())
    p_dict["tenant_id"] = tenant_id
    result = await db.payments.insert_one(p_dict)
    p_dict["_id"] = str(result.inserted_id)
    return p_dict

@router.get("/expenses", response_model=List[schemas.Expense])
async def read_expenses(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    expenses = await db.expenses.find().to_list(length=100)
    for e in expenses: e["_id"] = str(e["_id"])
    return expenses

@router.post("/expense", response_model=schemas.Expense)
async def create_expense(expense: schemas.ExpenseCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    e_dict = prepare_mongo_data(expense.dict())
    result = await db.expenses.insert_one(e_dict)
    e_dict["_id"] = str(result.inserted_id)
    return e_dict

@router.get("/maintenance", response_model=List[schemas.Maintenance])
async def read_maintenance(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    m_list = await db.maintenance.find().to_list(length=100)
    for m in m_list: m["_id"] = str(m["_id"])
    return m_list

@router.post("/maintenance", response_model=schemas.Maintenance)
async def create_maintenance(maintenance: schemas.MaintenanceCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    m_dict = prepare_mongo_data(maintenance.dict())
    result = await db.maintenance.insert_one(m_dict)
    m_dict["_id"] = str(result.inserted_id)
    return m_dict

@router.patch("/maintenance/{m_id}", response_model=schemas.Maintenance)
async def update_maintenance(m_id: str, m_update: schemas.MaintenanceUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    result = await db.maintenance.find_one_and_update({"_id": ObjectId(m_id)}, {"$set": m_update.dict(exclude_unset=True)}, return_document=True)
    if not result: raise HTTPException(status_code=404, detail="Not found")
    result["_id"] = str(result["_id"])
    return result

@router.post("/document/upload/{tenant_id}", response_model=schemas.Document)
async def upload_document(tenant_id: str, name: str = Form(...), doc_type: str = Form(...), file: UploadFile = File(...), db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    upload_result = cloudinary.uploader.upload(file.file, folder="house_kyc")
    doc_dict = {"tenant_id": tenant_id, "name": name, "type": doc_type, "file_path": upload_result.get("secure_url"), "public_id": upload_result.get("public_id"), "upload_date": datetime.now()}
    result = await db.documents.insert_one(doc_dict)
    doc_dict["_id"] = str(result.inserted_id)
    return doc_dict

@router.get("/documents/{tenant_id}", response_model=List[schemas.Document])
async def get_documents(tenant_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    docs = await db.documents.find({"tenant_id": tenant_id}).to_list(length=100)
    for d in docs: d["_id"] = str(d["_id"])
    return docs

@router.delete("/document/{doc_id}")
async def delete_document(doc_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"status": "success"}

@router.post("/note", response_model=schemas.Note)
async def create_note(note: schemas.NoteCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    n_dict = note.dict()
    result = await db.notes.insert_one(n_dict)
    n_dict["_id"] = str(result.inserted_id)
    return n_dict

@router.get("/notes", response_model=List[schemas.Note])
async def read_notes(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    notes = await db.notes.find().sort("created_at", -1).to_list(length=100)
    for n in notes: n["_id"] = str(n["_id"])
    return notes

@router.patch("/note/{note_id}", response_model=schemas.Note)
async def update_note(note_id: str, note_update: schemas.NoteUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    u_data = {k: v for k, v in note_update.dict().items() if v is not None}
    u_data["updated_at"] = datetime.now()
    result = await db.notes.find_one_and_update({"_id": ObjectId(note_id)}, {"$set": u_data}, return_document=True)
    result["_id"] = str(result["_id"])
    return result

@router.delete("/note/{note_id}")
async def delete_note(note_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    await db.notes.delete_one({"_id": ObjectId(note_id)})
    return {"status": "success"}

app.include_router(router, prefix="/api")
