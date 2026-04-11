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

# SETUP PATHS FOR VERCEL
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# RELATIVE IMPORTS
import schemas
import auth
import database

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

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "database_connected": database.db is not None,
        "db_error": database.db_error,
        "env_keys": [k for k in os.environ.keys() if "URL" in k or "SECRET" in k or "KEY" in k or "NAME" in k]
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

# ... (rest of the endpoints simplified for now to ensure startup) ...
@router.post("/tenant", response_model=schemas.Tenant)
async def create_tenant(tenant: schemas.TenantCreate, db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    t_dict = tenant.dict()
    for k,v in t_dict.items(): 
        if isinstance(v, date): t_dict[k] = datetime.combine(v, datetime.min.time())
    res = await db.tenants.insert_one(t_dict)
    t_dict["_id"] = str(res.inserted_id)
    t_dict["payments"] = []; t_dict["documents"] = []
    return t_dict

@router.get("/expenses", response_model=List[schemas.Expense])
async def get_expenses(db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.expenses.find().to_list(100)
    for e in res: e["_id"] = str(e["_id"])
    return res

@router.get("/maintenance", response_model=List[schemas.Maintenance])
async def get_m(db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.maintenance.find().to_list(100)
    for m in res: m["_id"] = str(m["_id"])
    return res

@router.get("/notes", response_model=List[schemas.Note])
async def get_notes(db = Depends(database.get_database), current_user = Depends(auth.get_current_user)):
    res = await db.notes.find().sort("created_at", -1).to_list(100)
    for n in res: n["_id"] = str(n["_id"])
    return res

# --- FINAL SETUP ---
app.include_router(router, prefix="/api")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
