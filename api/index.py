from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import io
import csv
from fpdf import FPDF
from typing import List, Optional
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, date, datetime
from bson import ObjectId
import logging
import os
import sys
from pathlib import Path
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# SETUP PATHS FOR VERCEL
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# RELATIVE IMPORTS
import schemas
import auth
import database

# Cloudinary Configuration
cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

app = FastAPI()

# Global exception handler to return JSON instead of HTML on crash
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "detail": "CRITICAL BACKEND CRASH",
            "error_message": str(exc),
            "traceback": traceback.format_exc()
        }
    )

router = APIRouter()

def prepare_mongo_data(data: dict):
    new_data = data.copy()
    for key, value in new_data.items():
        if isinstance(value, (date, datetime)):
            if isinstance(value, date) and not isinstance(value, datetime):
                new_data[key] = datetime.combine(value, datetime.min.time())
    return new_data

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "database_connected": database.db is not None,
        "db_error": database.db_error
    }

# --- AUTHENTICATION ---
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(database.get_database)):
    try:
        user = await db.users.find_one({"username": form_data.username})
        if not user or not auth.verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Login Logic Error: {str(e)}")

# --- TENANTS ---
@router.get("/tenants", response_model=List[schemas.Tenant])
async def read_tenants(status: Optional[str] = None, search: Optional[str] = None, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    try:
        query = {}
        if status and status != "All": query["status"] = status
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"room_number": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}}
            ]
        
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

@router.post("/tenant", response_model=schemas.Tenant)
async def create_tenant(tenant: schemas.TenantCreate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    t_dict = prepare_mongo_data(tenant.dict())
    res = await db.tenants.insert_one(t_dict)
    t_dict["_id"] = str(res.inserted_id)
    t_dict["payments"] = []; t_dict["documents"] = []
    return t_dict

@router.patch("/tenant/{tenant_id}", response_model=schemas.Tenant)
async def update_tenant(tenant_id: str, tenant_update: schemas.TenantUpdate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    update_data = prepare_mongo_data(tenant_update.dict(exclude_unset=True))
    if not update_data: raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.tenants.find_one_and_update({"_id": ObjectId(tenant_id)}, {"$set": update_data}, return_document=True)
    if not result: raise HTTPException(status_code=404, detail="Tenant not found")
    result["_id"] = str(result["_id"])
    result["payments"] = [dict(p, _id=str(p["_id"])) for p in await db.payments.find({"tenant_id": tenant_id}).to_list(100)]
    result["documents"] = [dict(d, _id=str(d["_id"])) for d in await db.documents.find({"tenant_id": tenant_id}).to_list(100)]
    return result

@router.get("/tenants/export")
async def export_tenants(status: Optional[str] = None, search: Optional[str] = None, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    try:
        query = {}
        if status and status != "All": query["status"] = status
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"room_number": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}}
            ]
        tenants = await db.tenants.find(query).to_list(1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Phone", "Room", "Rent", "Move-in", "Status"])
        for t in tenants:
            move_in = t.get("move_in_date")
            if isinstance(move_in, datetime): move_in = move_in.strftime("%Y-%m-%d")
            writer.writerow([t.get("name"), t.get("phone"), t.get("room_number"), t.get("rent_amount"), move_in, t.get("status")])
        output.seek(0)
        return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=tenants_{date.today()}.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tenant/{tenant_id}/pdf")
async def export_tenant_pdf(tenant_id: str, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    try:
        tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
        if not tenant: raise HTTPException(status_code=404, detail="Tenant not found")
        payments = await db.payments.find({"tenant_id": tenant_id}).to_list(100)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, f"Tenant Report: {tenant.get('name')}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 8, f"Room: {tenant.get('room_number')}", ln=True)
        pdf.cell(190, 8, f"Phone: {tenant.get('phone')}", ln=True)
        pdf.cell(190, 8, f"Rent: Rs. {tenant.get('rent_amount')}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(40, 8, "Month", 1); pdf.cell(40, 8, "Year", 1); pdf.cell(40, 8, "Amount", 1); pdf.cell(40, 8, "Status", 1); pdf.ln()
        pdf.set_font("Arial", '', 12)
        for p in payments:
            pdf.cell(40, 8, str(p.get("month")), 1); pdf.cell(40, 8, str(p.get("year")), 1); pdf.cell(40, 8, str(p.get("amount")), 1); pdf.cell(40, 8, str(p.get("status")), 1); pdf.ln()
        return StreamingResponse(io.BytesIO(pdf.output(dest='S')), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=tenant_{tenant_id}.pdf"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PAYMENTS ---
@router.get("/payments/{tenant_id}", response_model=List[schemas.Payment])
async def read_payments(tenant_id: str, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    payments = await db.payments.find({"tenant_id": tenant_id}).to_list(100)
    for p in payments: p["_id"] = str(p["_id"])
    return payments

@router.post("/payment/{tenant_id}", response_model=schemas.Payment)
async def create_payment(tenant_id: str, payment: schemas.PaymentCreate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    payment_dict = prepare_mongo_data(payment.dict())
    payment_dict["tenant_id"] = tenant_id
    payment_dict["updated_at"] = datetime.utcnow()
    result = await db.payments.insert_one(payment_dict)
    payment_dict["_id"] = str(result.inserted_id)
    return payment_dict

# --- DOCUMENTS ---
@router.post("/document/upload/{tenant_id}", response_model=schemas.Document)
async def upload_document(tenant_id: str, name: str = Form(...), doc_type: str = Form(...), file: UploadFile = File(...), db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    try:
        upload_result = cloudinary.uploader.upload(file.file)
        doc_dict = {"tenant_id": tenant_id, "name": name, "type": doc_type, "file_path": upload_result.get("secure_url"), "cloudinary_id": upload_result.get("public_id"), "upload_date": datetime.utcnow()}
        result = await db.documents.insert_one(doc_dict)
        doc_dict["_id"] = str(result.inserted_id)
        return doc_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@router.get("/documents/{tenant_id}", response_model=List[schemas.Document])
async def read_documents(tenant_id: str, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    docs = await db.documents.find({"tenant_id": tenant_id}).to_list(100)
    for d in docs: d["_id"] = str(d["_id"])
    return docs

@router.delete("/document/{doc_id}")
async def delete_document(doc_id: str, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if doc and doc.get("cloudinary_id"): cloudinary.uploader.destroy(doc["cloudinary_id"])
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"status": "deleted"}

# --- EXPENSES ---
@router.get("/expenses", response_model=List[schemas.Expense])
async def get_expenses(db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.expenses.find().to_list(100)
    for e in res: e["_id"] = str(e["_id"])
    return res

@router.patch("/expense/{expense_id}", response_model=schemas.Expense)
async def update_expense(expense_id: str, expense_update: schemas.ExpenseUpdate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    update_data = prepare_mongo_data(expense_update.dict(exclude_unset=True))
    if not update_data: raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.expenses.find_one_and_update({"_id": ObjectId(expense_id)}, {"$set": update_data}, return_document=True)
    if not result: raise HTTPException(status_code=404, detail="Expense not found")
    result["_id"] = str(result["_id"])
    return result

@router.delete("/expense/{expense_id}")
async def delete_expense(expense_id: str, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    await db.expenses.delete_one({"_id": ObjectId(expense_id)})
    return {"status": "deleted"}

@router.post("/expense", response_model=schemas.Expense)
async def create_expense(expense: schemas.ExpenseCreate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    expense_dict = prepare_mongo_data(expense.dict())
    result = await db.expenses.insert_one(expense_dict)
    expense_dict["_id"] = str(result.inserted_id)
    return expense_dict

# --- MAINTENANCE ---
@router.get("/maintenance", response_model=List[schemas.Maintenance])
async def get_m(db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.maintenance.find().to_list(100)
    for m in res: m["_id"] = str(m["_id"])
    return res

@router.post("/maintenance", response_model=schemas.Maintenance)
async def create_maintenance(maintenance: schemas.MaintenanceCreate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    m_dict = prepare_mongo_data(maintenance.dict())
    result = await db.maintenance.insert_one(m_dict)
    m_dict["_id"] = str(result.inserted_id)
    return m_dict

@router.patch("/maintenance/{m_id}", response_model=schemas.Maintenance)
async def update_m(m_id: str, m_update: schemas.MaintenanceUpdate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.maintenance.find_one_and_update({"_id": ObjectId(m_id)}, {"$set": prepare_mongo_data(m_update.dict(exclude_unset=True))}, return_document=True)
    if not res: raise HTTPException(status_code=404, detail="Maintenance request not found")
    res["_id"] = str(res["_id"])
    return res

# --- NOTES ---
@router.get("/notes", response_model=List[schemas.Note])
async def get_notes(db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.notes.find().sort("created_at", -1).to_list(100)
    for n in res: n["_id"] = str(n["_id"])
    return res

@router.post("/note", response_model=schemas.Note)
async def create_note(note: schemas.NoteCreate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    n_dict = prepare_mongo_data(note.dict())
    n_dict["created_at"] = datetime.utcnow()
    result = await db.notes.insert_one(n_dict)
    n_dict["_id"] = str(result.inserted_id)
    return n_dict

@router.patch("/note/{note_id}", response_model=schemas.Note)
async def update_note(note_id: str, note_update: schemas.NoteUpdate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.notes.find_one_and_update({"_id": ObjectId(note_id)}, {"$set": note_update.dict(exclude_unset=True)}, return_document=True)
    if not res: raise HTTPException(status_code=404, detail="Note not found")
    res["_id"] = str(res["_id"])
    return res

@router.delete("/note/{note_id}")
async def delete_note(note_id: str, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    await db.notes.delete_one({"_id": ObjectId(note_id)})
    return {"status": "deleted"}

# --- FINAL SETUP ---
app.include_router(router, prefix="/api")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
