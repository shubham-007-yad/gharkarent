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

# --- HEALTH ENDPOINTS (Direct on App for maximum reliability) ---
@app.get("/api/health")
@app.get("/health")
@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

# --- AUTHENTICATION ---
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_database)):
    try:
        user = await db.users.find_one({"username": form_data.username})
        if not user or not auth.verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

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

# --- TENANTS ---
@router.post("/tenant", response_model=schemas.Tenant)
async def create_tenant(tenant: schemas.TenantCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        tenant_dict = tenant.dict()
        for k, v in tenant_dict.items():
            if isinstance(v, date):
                tenant_dict[k] = datetime.combine(v, datetime.min.time())
        result = await db.tenants.insert_one(tenant_dict)
        tenant_dict["_id"] = str(result.inserted_id)
        tenant_dict["payments"] = []
        tenant_dict["documents"] = []
        return tenant_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tenants", response_model=List[schemas.Tenant])
async def read_tenants(status: Optional[str] = None, min_rent: Optional[float] = None, max_rent: Optional[float] = None, search: Optional[str] = None, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        query = {}
        if status and status != "All": query["status"] = status
        if min_rent is not None or max_rent is not None:
            query["rent_amount"] = {}
            if min_rent is not None: query["rent_amount"]["$gte"] = min_rent
            if max_rent is not None: query["rent_amount"]["$lte"] = max_rent
        if search:
            query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"room_number": {"$regex": search, "$options": "i"}}]
        
        cursor = db.tenants.find(query)
        tenants = await cursor.to_list(length=100)
        for t in tenants:
            t["_id"] = str(t["_id"])
            t_id = t["_id"]
            t["payments"] = [dict(p, _id=str(p["_id"])) for p in await db.payments.find({"tenant_id": t_id}).to_list(100)]
            t["documents"] = [dict(d, _id=str(d["_id"])) for d in await db.documents.find({"tenant_id": t_id}).to_list(100)]
        return tenants
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tenants/export")
async def export_tenants(status: Optional[str] = None, search: Optional[str] = None, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        cursor = db.tenants.find({})
        tenants = await cursor.to_list(1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Phone", "Room"])
        for t in tenants:
            writer.writerow([t.get("name"), t.get("phone"), t.get("room_number")])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=export.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tenant/{tenant_id}/pdf")
async def export_pdf(tenant_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Tenant Report", ln=1, align="C")
    return StreamingResponse(io.BytesIO(pdf.output(dest='S')), media_type="application/pdf")

@router.patch("/tenant/{tenant_id}", response_model=schemas.Tenant)
async def update_tenant(tenant_id: str, update: schemas.TenantUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.tenants.find_one_and_update({"_id": ObjectId(tenant_id)}, {"$set": update.dict(exclude_unset=True)}, return_document=True)
    if not res: raise HTTPException(status_code=404)
    res["_id"] = str(res["_id"])
    return res

# --- PAYMENTS ---
@router.post("/payment/{tenant_id}", response_model=schemas.Payment)
async def create_payment(tenant_id: str, payment: schemas.PaymentCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    p_dict = payment.dict()
    p_dict["tenant_id"] = tenant_id
    result = await db.payments.insert_one(p_dict)
    p_dict["_id"] = str(result.inserted_id)
    return p_dict

# --- EXPENSES ---
@router.get("/expenses", response_model=List[schemas.Expense])
async def get_expenses(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.expenses.find().to_list(100)
    for e in res: e["_id"] = str(e["_id"])
    return res

@router.post("/expense", response_model=schemas.Expense)
async def create_expense(expense: schemas.ExpenseCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    e_dict = expense.dict()
    result = await db.expenses.insert_one(e_dict)
    e_dict["_id"] = str(result.inserted_id)
    return e_dict

# --- MAINTENANCE ---
@router.get("/maintenance", response_model=List[schemas.Maintenance])
async def get_m(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.maintenance.find().to_list(100)
    for m in res: m["_id"] = str(m["_id"])
    return res

@router.post("/maintenance", response_model=schemas.Maintenance)
async def create_m(maintenance: schemas.MaintenanceCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    m_dict = maintenance.dict()
    result = await db.maintenance.insert_one(m_dict)
    m_dict["_id"] = str(result.inserted_id)
    return m_dict

@router.patch("/maintenance/{m_id}", response_model=schemas.Maintenance)
async def update_m(m_id: str, update: schemas.MaintenanceUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.maintenance.find_one_and_update({"_id": ObjectId(m_id)}, {"$set": update.dict(exclude_unset=True)}, return_document=True)
    res["_id"] = str(res["_id"])
    return res

# --- DOCUMENTS ---
@router.post("/document/upload/{tenant_id}", response_model=schemas.Document)
async def upload_doc(tenant_id: str, name: str = Form(...), doc_type: str = Form(...), file: UploadFile = File(...), db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    up = cloudinary.uploader.upload(file.file, folder="house_kyc")
    doc = {"tenant_id": tenant_id, "name": name, "type": doc_type, "file_path": up.get("secure_url"), "public_id": up.get("public_id"), "upload_date": datetime.now()}
    result = await db.documents.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@router.get("/documents/{tenant_id}", response_model=List[schemas.Document])
async def get_docs(tenant_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.documents.find({"tenant_id": tenant_id}).to_list(100)
    for d in res: d["_id"] = str(d["_id"])
    return res

@router.delete("/document/{doc_id}")
async def del_doc(doc_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"status": "success"}

# --- NOTES ---
@router.get("/notes", response_model=List[schemas.Note])
async def get_notes(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.notes.find().sort("created_at", -1).to_list(100)
    for n in res: n["_id"] = str(n["_id"])
    return res

@router.post("/note", response_model=schemas.Note)
async def create_note(note: schemas.NoteCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    n_dict = note.dict()
    result = await db.notes.insert_one(n_dict)
    n_dict["_id"] = str(result.inserted_id)
    return n_dict

@router.patch("/note/{note_id}", response_model=schemas.Note)
async def update_note(note_id: str, update: schemas.NoteUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    res = await db.notes.find_one_and_update({"_id": ObjectId(note_id)}, {"$set": update.dict(exclude_unset=True)}, return_document=True)
    res["_id"] = str(res["_id"])
    return res

@router.delete("/note/{note_id}")
async def del_note(note_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    await db.notes.delete_one({"_id": ObjectId(note_id)})
    return {"status": "success"}

# --- ROUTER INCLUSION ---
app.include_router(router, prefix="/api")
app.include_router(router)

# Mount uploads directory safely (Vercel is read-only)
try:
    if not os.path.exists("/tmp/uploads"):
        os.makedirs("/tmp/uploads")
    app.mount("/uploads", StaticFiles(directory="/tmp/uploads"), name="uploads")
except:
    pass

# Mount React static assets
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Enable CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

# CATCH-ALL FOR REACT FRONTEND (MUST BE AT THE VERY END)
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    # If the file exists physically (like assets/...), StaticFiles would handle it
    # Otherwise, return index.html for React routing
    return FileResponse("index.html")
