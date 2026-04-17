from pydantic import BaseModel, Field, BeforeValidator
from typing import List, Optional, Annotated, Any
from datetime import date, datetime
from bson import ObjectId

# Custom type for handling MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

# Custom validator to handle datetimes coming from MongoDB as dates
def validate_date(v: Any) -> Any:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            # Handle ISO format and simple YYYY-MM-DD
            return date.fromisoformat(v.split('T')[0])
        except Exception:
            return None
    return v

FlexibleDate = Annotated[date, BeforeValidator(validate_date)]
OptionalFlexibleDate = Annotated[Optional[date], BeforeValidator(validate_date)]

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(MongoBaseModel, UserBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Payment Schemas
class PaymentBase(BaseModel):
    amount: float
    pending_amount: float = 0.0
    initial_reading: float = 0.0
    current_reading: float = 0.0
    rate_per_unit: float = 0.0
    electricity_amount: float = 0.0
    date: OptionalFlexibleDate = None
    month: str 
    year: int 
    method: str = "Cash" 
    status: str
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    pending_amount: Optional[float] = None
    initial_reading: Optional[float] = None
    current_reading: Optional[float] = None
    rate_per_unit: Optional[float] = None
    electricity_amount: Optional[float] = None
    date: Optional[FlexibleDate] = None
    month: Optional[str] = None
    year: Optional[int] = None
    method: Optional[str] = None
    status: Optional[str] = None

class Payment(MongoBaseModel, PaymentBase):
    tenant_id: str

# Document Schemas
class DocumentBase(BaseModel):
    name: str
    type: str # Aadhar, PAN, Agreement, Other
    file_path: str
    public_id: Optional[str] = None
    upload_date: Optional[datetime] = Field(default_factory=datetime.now)

class DocumentCreate(DocumentBase):
    pass

class Document(MongoBaseModel, DocumentBase):
    tenant_id: str

# Tenant Schemas
class TenantBase(BaseModel):
    name: str
    phone: Optional[str] = None
    room_number: Optional[str] = None
    rent_amount: float = 0.0
    move_in_date: OptionalFlexibleDate = None
    move_out_date: OptionalFlexibleDate = None
    status: str = "active"
    aadhar_number: Optional[str] = Field(None, min_length=12, max_length=16, pattern=r"^\d{12}(\d{4})?$")
    emergency_contact: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r"^\d{10}$")

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    room_number: Optional[str] = None
    rent_amount: Optional[float] = None
    move_in_date: Optional[FlexibleDate] = None
    move_out_date: Optional[FlexibleDate] = None
    status: Optional[str] = None
    aadhar_number: Optional[str] = Field(None, min_length=12, max_length=16, pattern=r"^\d{12}(\d{4})?$")
    emergency_contact: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r"^\d{10}$")

class Tenant(MongoBaseModel, TenantBase):
    payments: List[Payment] = []
    documents: List[Document] = []

# Expense Schemas
class ExpenseBase(BaseModel):
    title: str
    amount: float
    category: str # Repair, Cleaning, Tax, Bill, Other
    date: OptionalFlexibleDate = None
    description: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    date: Optional[FlexibleDate] = None
    description: Optional[str] = None

class Expense(MongoBaseModel, ExpenseBase):
    pass

# Maintenance Schemas
class MaintenanceBase(BaseModel):
    tenant_id: str
    tenant_name: str
    issue: str
    notes: Optional[str] = None
    priority: str # Low, Medium, High
    status: str = "pending" # pending, in_progress, resolved
    cost: Optional[float] = 0.0
    created_at: OptionalFlexibleDate

class MaintenanceCreate(MaintenanceBase):
    pass

class MaintenanceUpdate(BaseModel):
    issue: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None
    cost: Optional[float] = None

class Maintenance(MongoBaseModel, MaintenanceBase):
    pass

# Note Schemas
class NoteBase(BaseModel):
    title: str
    content: str
    category: str = "General" # General, Urgent, Private, etc.
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

class Note(MongoBaseModel, NoteBase):
    pass
