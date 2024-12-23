from sqlalchemy import Boolean, Column, Integer, String, Enum, Date, ForeignKey, Time
from database import Base
from enum import Enum as PyEnum
import random
from sqlalchemy.orm import relationship




# Model For Doctors Table
def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.regno = random.randint(1000, 9999)

def generate_unique_regno(db):
    while True:
        regno = random.randint(1000, 9999)
        if not db.query(Doctor).filter(Doctor.regno == regno).first():
            return regno

class Doctor(Base):
    __tablename__ = 'doctors'
    
    id =Column(Integer, primary_key=True, index=True)
    regno = Column(String(4), unique=True, nullable=False)
    firstname = Column(String(15),nullable=False)
    lastname = Column(String(15),nullable=False)
    department = Column(String(30), nullable=False)
    mobile = Column(String(10), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    appointments = relationship("Appointment", back_populates="doctor")
    
    

# Model for Paatient Table  
def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate a random 10-digit integer UID
        self.uid = random.randint(1000000000, 9999999999)

def generate_unique_uid(db):
    while True:
        uid = random.randint(1000000000, 9999999999)
        if not db.query(Patient).filter(Patient.uid == uid).first():
            return uid

class Patientgender(PyEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(10), unique=True, nullable=False)
    firstname = Column(String(15), nullable=False)
    middlename = Column(String(15), nullable=False)
    lastname = Column(String(15), nullable=False)
    gender = Column(Enum(Patientgender))
    address = Column(String(60), nullable=False)
    disease = Column(String(50))
    password_hash = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)  
    mobile_number = Column(String(15), nullable=False) 
    age = Column(Integer)
    is_deleted = Column(Boolean, default=False)
    
    
    appointments = relationship("Appointment", back_populates="patient")
    

# Models for Appointment Table
class AppointmentStatus(PyEnum):
    PENDING = "PENDING"
    CHECKED = "CHECKED"

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(10), ForeignKey("patients.uid"), nullable=False)
    doctor_regno = Column(String(4), ForeignKey("doctors.regno"), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(String(10), nullable=False)
    day = Column(String(10), nullable=False)  # Store day as a string (e.g., 'Monday')
    symptoms = Column(String(255))
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    is_deleted = Column(Boolean, default=False)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    

    