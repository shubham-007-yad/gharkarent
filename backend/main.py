from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, date, datetime
from bson import ObjectId
import logging
import os
import shutil
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

import schemas, auth
from database import get_database

# Cloudinary Configuration
cloudinary.config( 
  cloud_name = "dxbbvlppl", 
  api_key = "436835433477921", 
  api_secret = "dJajvptSYysIAoQ40u7ajVER-OQ",
  secure = True
)

app = FastAPI()

# Mount uploads directory to serve files
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Specific origins for CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Helper function to convert dates for MongoDB
def prepare_mongo_data(data: dict):
    new_data = data.copy()
    for key, value in new_data.items():
        if isinstance(value, date):
            # Ensure we use 00:00:00 for dates
            new_data[key] = datetime.combine(value, datetime.min.time())
    return new_data

# Authentication Endpoints
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_database)):
    try:
        user = await db.users.find_one({"username": form_data.username})
        if not user:
            print(f"Login failure: User {form_data.username} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        is_valid = auth.verify_password(form_data.password, user["hashed_password"])
        if not is_valid:
            print(f"Login failure: Invalid password for {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"CRITICAL LOGIN ERROR: {str(e)}")
        # If it's already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise e
        # Otherwise, return a 500 with the error message for debugging
        raise HTTPException(status_code=500, detail=f"Database or Server Error: {str(e)}")

@app.post("/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db = Depends(get_database)):
    db_user = await db.users.find_one({"username": user.username})
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user_dict = user.dict()
    new_user_dict["hashed_password"] = hashed_password
    del new_user_dict["password"]
    
    result = await db.users.insert_one(new_user_dict)
    new_user_dict["_id"] = result.inserted_id
    return new_user_dict

# Tenant Endpoints
@app.post("/tenant", response_model=schemas.Tenant)
async def create_tenant(tenant: schemas.TenantCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        tenant_dict = prepare_mongo_data(tenant.dict())
        result = await db.tenants.insert_one(tenant_dict)
        tenant_dict["_id"] = str(result.inserted_id)
        
        # Initialize empty lists for response model
        tenant_dict["payments"] = []
        tenant_dict["documents"] = []
        
        return tenant_dict
    except Exception as e:
        logger.error(f"Error in create_tenant: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create rental person: {str(e)}")

@app.get("/tenants", response_model=List[schemas.Tenant])
async def read_tenants(skip: int = 0, limit: int = 100, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    try:
        tenants_cursor = db.tenants.find().skip(skip).limit(limit)
        tenants = await tenants_cursor.to_list(length=limit)
        
        # Attach payments and documents to each tenant
        for tenant in tenants:
            tenant["_id"] = str(tenant["_id"])
            tenant_id_str = tenant["_id"]
            
            payments = await db.payments.find({"tenant_id": tenant_id_str}).to_list(length=100)
            for p in payments:
                p["_id"] = str(p["_id"])
            tenant["payments"] = payments
            
            documents = await db.documents.find({"tenant_id": tenant_id_str}).to_list(length=100)
            for d in documents:
                d["_id"] = str(d["_id"])
            tenant["documents"] = documents
            
        results = []
        for t in tenants:
            try:
                results.append(schemas.Tenant(**t))
            except Exception as val_err:
                logger.error(f"Validation error for tenant {t.get('_id')}: {str(val_err)}")
                # Skip the bad tenant instead of crashing
                continue
            
        return results
    except Exception as e:
        logger.error(f"Error in read_tenants: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database or processing error: {str(e)}")

@app.patch("/tenant/{tenant_id}", response_model=schemas.Tenant)
async def update_tenant(tenant_id: str, tenant_update: schemas.TenantUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    update_data = prepare_mongo_data(tenant_update.dict(exclude_unset=True))
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.tenants.find_one_and_update(
        {"_id": ObjectId(tenant_id)},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Rental person not found")
    
    result["_id"] = str(result["_id"])
    
    # Attach payments and documents
    payments = await db.payments.find({"tenant_id": tenant_id}).to_list(length=100)
    for p in payments:
        p["_id"] = str(p["_id"])
    result["payments"] = payments
    
    documents = await db.documents.find({"tenant_id": tenant_id}).to_list(length=100)
    for d in documents:
        d["_id"] = str(d["_id"])
    result["documents"] = documents
    
    return result

# Payment Endpoints
@app.post("/payment/{tenant_id}", response_model=schemas.Payment)
async def create_payment(tenant_id: str, payment: schemas.PaymentCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    payment_dict = prepare_mongo_data(payment.dict())
    payment_dict["tenant_id"] = tenant_id
    
    result = await db.payments.insert_one(payment_dict)
    payment_dict["_id"] = str(result.inserted_id)
    return payment_dict

@app.get("/payments/{tenant_id}", response_model=List[schemas.Payment])
async def read_payments(tenant_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    payments_cursor = db.payments.find({"tenant_id": tenant_id})
    payments = await payments_cursor.to_list(length=100)
    for p in payments:
        p["_id"] = str(p["_id"])
    return payments

# Expense Endpoints
@app.post("/expense", response_model=schemas.Expense)
async def create_expense(expense: schemas.ExpenseCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    expense_dict = prepare_mongo_data(expense.dict())
    result = await db.expenses.insert_one(expense_dict)
    expense_dict["_id"] = str(result.inserted_id)
    return expense_dict

@app.get("/expenses", response_model=List[schemas.Expense])
async def read_expenses(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    expenses_cursor = db.expenses.find()
    expenses = await expenses_cursor.to_list(length=100)
    for e in expenses:
        e["_id"] = str(e["_id"])
    return expenses

# Maintenance Endpoints
@app.post("/maintenance", response_model=schemas.Maintenance)
async def create_maintenance(maintenance: schemas.MaintenanceCreate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    m_dict = prepare_mongo_data(maintenance.dict())
    result = await db.maintenance.insert_one(m_dict)
    m_dict["_id"] = str(result.inserted_id)
    return m_dict

@app.get("/maintenance", response_model=List[schemas.Maintenance])
async def read_maintenance(db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    m_cursor = db.maintenance.find()
    maintenance_list = await m_cursor.to_list(length=100)
    for m in maintenance_list:
        m["_id"] = str(m["_id"])
    return maintenance_list

@app.patch("/maintenance/{m_id}", response_model=schemas.Maintenance)
async def update_maintenance(m_id: str, m_update: schemas.MaintenanceUpdate, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    # Check if it is already resolved
    existing = await db.maintenance.find_one({"_id": ObjectId(m_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    
    if existing.get("status") == "resolved":
        raise HTTPException(status_code=400, detail="Cannot update a resolved maintenance request")

    result = await db.maintenance.find_one_and_update(
        {"_id": ObjectId(m_id)},
        {"$set": m_update.dict(exclude_unset=True)},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    result["_id"] = str(result["_id"])
    return result

# Document Endpoints
@app.post("/document/upload/{tenant_id}", response_model=schemas.Document)
async def upload_document(
    tenant_id: str,
    name: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db = Depends(get_database),
    current_user = Depends(auth.get_current_user)
):
    # Ensure tenant exists
    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    try:
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file, 
            folder="house_kyc",
            public_id=f"{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            resource_type="auto"
        )
        
        file_url = upload_result.get("secure_url")
        public_id = upload_result.get("public_id")
        
        # Store in DB
        doc_dict = {
            "tenant_id": tenant_id,
            "name": name,
            "type": doc_type,
            "file_path": file_url,
            "public_id": public_id,
            "upload_date": datetime.now()
        }
        
        result = await db.documents.insert_one(doc_dict)
        doc_dict["_id"] = str(result.inserted_id)
        return doc_dict
    except Exception as e:
        logger.error(f"Cloudinary upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading document to cloud")

@app.get("/documents/{tenant_id}", response_model=List[schemas.Document])
async def get_documents(tenant_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    docs_cursor = db.documents.find({"tenant_id": tenant_id})
    docs = await docs_cursor.to_list(length=100)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

@app.delete("/document/{doc_id}")
async def delete_document(doc_id: str, db = Depends(get_database), current_user = Depends(auth.get_current_user)):
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    try:
        # Delete from Cloudinary if public_id exists
        if "public_id" in doc and doc["public_id"]:
            cloudinary.uploader.destroy(doc["public_id"])
        
        # Delete from DB
        await db.documents.delete_one({"_id": ObjectId(doc_id)})
        return {"status": "success", "message": "Document deleted"}
    except Exception as e:
        logger.error(f"Cloudinary delete error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting document from cloud")
