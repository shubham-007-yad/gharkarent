from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String)
    room_number = Column(String)
    rent_amount = Column(Float, default=0.0)
    move_in_date = Column(Date)
    move_out_date = Column(Date, nullable=True)
    status = Column(String, default="active") # active, leaving, inactive

    payments = relationship("Payment", back_populates="tenant")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    amount = Column(Float) # Amount Submitted
    pending_amount = Column(Float, default=0.0) # Amount Owed/Pending
    
    # Electricity fields
    initial_reading = Column(Float, default=0.0)
    current_reading = Column(Float, default=0.0)
    rate_per_unit = Column(Float, default=0.0)
    electricity_amount = Column(Float, default=0.0)
    
    date = Column(Date) 
    month = Column(String) 
    year = Column(Integer) 
    method = Column(String, default="Cash") 
    status = Column(String) # paid, pending, partial

    tenant = relationship("Tenant", back_populates="payments")
