from fastapi import FastAPI, HTTPException, Depends, status, Path, Query, Request
from pydantic import BaseModel
from typing import Annotated
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext
from datetime import date
from typing import Optional
from datetime import datetime
from enum import Enum
import jwt
from jwt import PyJWTError
from sqlalchemy import cast, Date
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
models.Base.metadata.create_all(bind=engine)




SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 1

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="doctor/login/")

# Models
class Doctor(BaseModel):
    firstname: str
    lastname: str
    department: str
    mobile: str
    password: str
    is_deleted: bool = False

    class Config:
        arbitrary_types_allowed = True
        
class DoctorLoginRequest(BaseModel):
    regno: int
    password: str
    
    
    class Config:
        arbitrary_types_allowed = True

class Patient(BaseModel):
    firstname: str
    middlename: str
    lastname: str 
    gender: str
    address: str
    password: str
    date_of_birth: date 
    mobile_number: str  
    age: int
    is_deleted: bool = False

    class Config:
        arbitrary_types_allowed = True 
        
class PatientLoginRequest(BaseModel):
    uid: int
    password: str
    
    
    class Config:
        arbitrary_types_allowed = True

class AppointmentStatusEnum(str, Enum):
    PENDING = "PENDING"
    CHECKED = "CHECKED"

class Appointment(BaseModel):
    patient_uid: int
    doctor_regno: int
    date_time: date
    day: str
    symptoms: str
    is_deleted: bool = False
    status: Optional[AppointmentStatusEnum] = AppointmentStatusEnum.PENDING


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Current Doctor Access Token
def get_current_doctor(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: db_dependency
):
    try:
        payload = verify_token(token)
        doctor_regno = payload.get("sub")
        if doctor_regno is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        doctor = db.query(models.Doctor).filter(
            models.Doctor.regno == doctor_regno,
            models.Doctor.is_deleted == False
        ).first()
        if doctor is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Doctor not found")
        return doctor
    except HTTPException as e:
        raise e

@app.get("/test-token")
def test_token(token: Annotated[str, Depends(oauth2_scheme)]):
    print(f"Token received: {token}")  # Debug
    payload = verify_token(token)
    return {"payload": payload}






# Doctors All API start Here
@app.post("/doctors/", status_code=status.HTTP_201_CREATED)
async def add_doctor(doctor: Doctor, db: db_dependency):
    hashed_password = hash_password(doctor.password)
    regno = models.generate_unique_regno(db)
    db_doctor = models.Doctor(
        regno=regno,
        firstname=doctor.firstname,
        lastname=doctor.lastname,
        department=doctor.department,
        mobile=doctor.mobile,
        password_hash=hashed_password
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

# Doctor Login
@app.post("/doctor/login/")
async def authenticate_doctor(doctor: DoctorLoginRequest, db: db_dependency):
    
    db_doctor = db.query(models.Doctor).filter(models.Doctor.regno == doctor.regno).first()

    if not db_doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    if db_doctor.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Doctor account is deleted")

    if not verify_password(doctor.password, db_doctor.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    access_token = create_access_token(data={"sub": str(db_doctor.regno)})
    refresh_token = create_refresh_token(data={"sub": str(db_doctor.regno)})

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "doctor_firstname": db_doctor.firstname + " " + db_doctor.lastname
    }
    
# Each Doctors All Apointments
@app.get("/doctor/{regno}/appointments", status_code=status.HTTP_200_OK)
async def get_appointments_for_doctor(regno: str, db: db_dependency):
    

    doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False).first()

   
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or has been deleted")

    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.doctor_regno == regno,
            models.Appointment.is_deleted == False
        )
        .all()
    )

    if not appointments:
        return {"detail": "No appointments found for this doctor"}

    doctor_appointments = {
        "doctor_name": f"{doctor.firstname} {doctor.lastname}",
        "regno": doctor.regno,
        "appointments": [
            {
                "appointment_id": appointment.id,
                "appointment_symptoms":appointment.symptoms,
                "date_time": appointment.date_time,
                "day": appointment.day,
                "is_deleted": appointment.is_deleted,
                "patient_info": {
                    "patient_name": f"{appointment.patient.firstname} {appointment.patient.lastname}",
                    "patient_uid": appointment.patient.uid,
                    "patient_disease":appointment.patient.disease,
                    "patient_mobile": appointment.patient.mobile_number,
                    "patient_address": appointment.patient.address
                }
            }
            for appointment in appointments
        ]
    }

    return {"doctor_appointments": doctor_appointments}

# get single apointment for each doctor
@app.get("/doctor/{regno}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def get_single_appointment_for_doctor(regno: str, appointment_id: int, db: db_dependency):
   
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False).first()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or has been deleted")

    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == regno,
            models.Appointment.is_deleted == False
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted"
        )

    patient = appointment.patient

    return {
        "doctor_name": f"{doctor.firstname} {doctor.lastname}",
        "regno": doctor.regno,
        "appointment": {
            "appointment_id": appointment.id,
            "appointment_symptoms":appointment.symptoms,
            "date_time": appointment.date_time,
            "day": appointment.day,
            "is_deleted": appointment.is_deleted,
            "patient_info": {
                "patient_name": f"{appointment.patient.firstname} {appointment.patient.lastname}",
                "patient_uid": appointment.patient.uid,
                "patient_disease":appointment.patient.disease,
                "patient_mobile": appointment.patient.mobile_number,
                "patient_address": appointment.patient.address
            }
        }
    }

# Update single apointment
@app.put("/doctor/{regno}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def update_appointment_and_patient_disease(regno: str, appointment_id: int, updated_data: dict, db: db_dependency):
    
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False).first()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or has been deleted")

    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == regno,
            models.Appointment.is_deleted == False
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted"
        )

    
    for key, value in updated_data.items():
        if hasattr(appointment, key) and value is not None:
            setattr(appointment, key, value)

   
    if "disease" in updated_data:
      
        patient = db.query(models.Patient).filter(models.Patient.uid == appointment.patient_uid).first()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
       
        patient.disease = updated_data["disease"]
        db.commit()
        db.refresh(patient)
        
    if "status" in updated_data:
        
        status = db.query(models.Appointment).filter(models.Appointment.id == appointment.id).first()
        
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
    Appointment.status = updated_data["status"]
    db.commit()
    db.refresh(appointment)

    return {
        "detail": "Appointment and patient diseases updated successfully",
        "appointment": {
            "appointment_id": appointment.id,
            "date_time": appointment.date_time,
            "day": appointment.day,
            "status":appointment.status,
            "is_deleted": appointment.is_deleted
        },
        "patient": {
            "patient_uid": appointment.patient_uid,
            "patient_name": f"{appointment.patient.firstname} {appointment.patient.lastname}",
            "diseases": patient.disease
        }
    }
    
# Delete each apointment of each doctor
@app.delete("/doctor/{regno}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def delete_appointment(regno: str, appointment_id: int, db: db_dependency):
   
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False).first()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or has been deleted")

    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == regno,
            models.Appointment.is_deleted == False
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted"
        )

    appointment.is_deleted = True
    db.commit()
    db.refresh(appointment)

    return {"detail": f"Appointment with id {appointment_id} has been marked as deleted"}


# Get all patient which are present and get apointments
@app.get("/doctors/{regno}/patients/with-appointments", status_code=status.HTTP_200_OK)
async def get_patients_for_doctor_with_appointments(regno: str, db: db_dependency):
    
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False).first()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or has been deleted")

    patients_with_appointments = (
        db.query(models.Patient)
        .join(models.Appointment, models.Appointment.patient_uid == models.Patient.uid)
        .filter(models.Appointment.doctor_regno == regno, models.Appointment.is_deleted == False)
        .group_by(models.Patient.uid)  
        .all()
    )

    if not patients_with_appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients with appointments found for this doctor"
        )

    return [
        {
            "patient_uid": patient.uid,
            "patient_name": f"{patient.firstname} {patient.lastname}",
            "appointments": [
                {
                    "appointment_id": appointment.id,
                    "date_time": appointment.date_time,
                    "status": appointment.status,
                    "is_deleted": appointment.is_deleted
                }
                for appointment in patient.appointments if appointment.doctor_regno == regno and appointment.is_deleted == False
            ]
        }
        for patient in patients_with_appointments
    ]
    
    
# Get Doctor Profile
@app.get("/doctor/{regno}/profile", status_code=status.HTTP_200_OK)
async def get_doctor_profile(regno: str, db: db_dependency):
    
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False).first()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or has been deleted")


    return {
        "doctor_profile": {
            "regno": doctor.regno,
            "doctor_name": f"{doctor.firstname} {doctor.lastname}",
            "department": doctor.department,
            "mobile": doctor.mobile,
        }
    }

# Update Doctor Profile
@app.put("/doctor/{regno}", status_code=status.HTTP_200_OK)
async def update_doctor(regno: str, updated_data: dict, db: db_dependency):
    
    db_doctor = db.query(models.Doctor).filter(models.Doctor.regno == regno).first()

    if not db_doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    if db_doctor.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Doctor account is deleted and cannot be updated")

    for key, value in updated_data.items():
        if hasattr(db_doctor, key) and value is not None:
            setattr(db_doctor, key, value)

    db.commit()
    db.refresh(db_doctor)

    return {
        "detail": f"Doctor with regno {regno} updated successfully",
        "updated_data": db_doctor
    }
    

# Delete doctor
@app.delete("/doctor/{regno}", status_code=status.HTTP_200_OK)
async def delete_doctor(regno: str, db: db_dependency):
    
    db_doctor = db.query(models.Doctor).filter
    if not db_doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    if db_doctor.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor is already deleted")

    # Mark the doctor as deleted by setting the `is_deleted` flag to True
    db_doctor.is_deleted = True

    db.commit()

    return {"detail": f"Doctor with regno {regno} has been marked as deleted"}



    
# Doctors All API Stop Here



# Patients All API Start Here
@app.post("/patient/", status_code=status.HTTP_201_CREATED)
async def add_patient(patient: Patient, db: db_dependency):
    hashed_password = hash_password(patient.password)
    uid = models.generate_unique_uid(db)
    db_patient = models.Patient(
        uid=uid,
        firstname=patient.firstname,
        middlename=patient.middlename,
        lastname=patient.lastname,
        gender=patient.gender,
        mobile_number=patient.mobile_number,
        age=patient.age,
        date_of_birth=patient.date_of_birth,
        address=patient.address,
        password_hash=hashed_password
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

# Patient Login
@app.post("/Patient/login/")
async def patient_authenticate(patient: PatientLoginRequest, db: db_dependency):
   
    db_patient = db.query(models.Patient).filter(models.Patient.uid == patient.uid).first()

    
    if not db_patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    
    if db_patient.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient account is deleted")

    
    if not verify_password(patient.password, db_patient.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    
    access_token = create_access_token(data={"sub": str(db_patient.uid)})
    refresh_token = create_refresh_token(data={"sub": str(db_patient.uid)})

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "patient_name": db_patient.firstname + " " + db_patient.lastname
    }

@app.post("/appointments", status_code=status.HTTP_201_CREATED)
async def create_appointment(appointment: Appointment, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.uid == appointment.patient_uid).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == appointment.doctor_regno).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    
    new_appointment = models.Appointment(
        patient_uid=patient.uid,
        doctor_regno=doctor.regno,
        date_time=appointment.date_time,
        day=appointment.day,
        symptoms=appointment.symptoms,
        status=appointment.status,
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return {"id": new_appointment.id, "patient_uid": appointment.patient_uid, "date_time": new_appointment.date_time, "day": new_appointment.day, "symptoms": new_appointment.symptoms, "status": new_appointment.status.value}

# Get All Apointments of each Patient
@app.get("/patient/{uid}/appointments", status_code=status.HTTP_200_OK)
async def get_patient_appointments(uid: str, db: db_dependency):
    
    db_patient = db.query(models.Patient).filter(models.Patient.uid == uid).first()

    
    if not db_patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    
    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account is deleted"
        )

    
    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_uid == db_patient.uid, 
            models.Appointment.is_deleted == False
        )
        .all()
    )

    return {
        "patient_name": f"{db_patient.firstname} {db_patient.lastname}",
        "appointments": appointments,
    }
    
# Get Single Appointment of each patient
@app.get("/patient/{uid}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def get_single_appointment(uid: str, appointment_id: int, db: db_dependency):
    
    db_patient = db.query(models.Patient).filter(models.Patient.uid == uid).first()

   
    if not db_patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    
    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account is deleted"
        )

    
    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,  
            models.Appointment.patient_uid == db_patient.uid,  
            models.Appointment.is_deleted == False  
        )
        .first()
    )

    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted"
        )

    
    doctor = db.query(models.Doctor).filter(models.Doctor.regno == appointment.doctor_regno).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found for the appointment"
        )

    return {
        "patient_name": f"{db_patient.firstname} {db_patient.lastname}",
        "appointment": {
            "id": appointment.id,
            "date_time": appointment.date_time,
            "day": appointment.day,
            "doctor_name": f"{doctor.firstname} {doctor.lastname}",
            "is_deleted": appointment.is_deleted
        }
    }
 
# Update Apointment using apointment id   
@app.put("/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def update_appointment(appointment_id: int, updated_data: dict, db: db_dependency):
    
    appointment = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    if appointment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a deleted appointment"
        )

    for key, value in updated_data.items():
        if hasattr(appointment, key) and value is not None:
            setattr(appointment, key, value)

    db.commit()
    db.refresh(appointment)

    return {
        "detail": f"Appointment with id {appointment_id} updated successfully",
        "updated_data": {
            "id": appointment.id,
            "date_time": appointment.date_time,
            "day": appointment.day,
            "doctor_regno": appointment.doctor_regno,
            "is_deleted": appointment.is_deleted
        }
    }
    
# Delete or Cancel Apointment
@app.delete("/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def delete_appointment(appointment_id: int, db: db_dependency):
   
    appointment = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()

   
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

   
    if appointment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Appointment with ID {appointment_id} is already marked as deleted"
        )

  
    appointment.is_deleted = True
    db.commit()

    return {"detail": f"Appointment with ID {appointment_id} has been marked as deleted"}

# Get all Doctors
@app.get("/doctors/", status_code=status.HTTP_200_OK)
async def get_all_doctors(db: db_dependency):
    
    doctors = (
        db.query(models.Doctor)
        .filter(models.Doctor.is_deleted == False)
        .all()
    )

    if not doctors:
        return {"detail": "No doctors available"}

    doctor_list = [
        {
            "id": doctor.id,
            "regno": doctor.regno,
            "firstname": doctor.firstname,
            "lastname": doctor.lastname,
            "department": doctor.department,
            "mobile": doctor.mobile
        }
        for doctor in doctors
    ]

    return {"doctors": doctor_list}


# Get single Doctor
@app.get("/doctor/{regno}", status_code=status.HTTP_200_OK)
async def get_single_doctor(regno: str, db: db_dependency):
    
    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted"
        )

    doctor_details = {
        "regno": doctor.regno,
        "firstname": doctor.firstname,
        "lastname": doctor.lastname,
        "department": doctor.department,
        "mobile": doctor.mobile
    }

    return {"doctor": doctor_details}


# Get Patient Profile
@app.get("/patient/{uid}/profile", status_code=status.HTTP_200_OK)
async def get_patient_profile(uid: str, db: db_dependency):
    
    patient = (
        db.query(models.Patient)
        .filter(models.Patient.uid == uid, models.Patient.is_deleted == False)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or has been deleted"
        )

    patient_profile = {
        "uid": patient.uid,
        "firstname": patient.firstname,
        "lastname": patient.lastname,
        "mobile_number": patient.mobile_number,
        "address": patient.address,
        "date_of_birth": patient.date_of_birth,
    }

    return {"patient": patient_profile}


# Update Patient Informatin
@app.put("/patient/{uid}", status_code=status.HTTP_200_OK)
async def update_patient(uid: str, updated_data: dict, db: db_dependency):
    
    db_patient = db.query(models.Patient).filter(models.Patient.uid == uid).first()

    
    if not db_patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    
    if db_patient.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient account is deleted and cannot be updated")

    
    for key, value in updated_data.items():
        if hasattr(db_patient, key) and value is not None:
            setattr(db_patient, key, value)
    
    
    db.commit()
    db.refresh(db_patient)

    return {
        "detail": f"Patient with uid {uid} updated successfully",
        "updated_data": db_patient
    }



# Delete Patient
@app.delete("/patient/{uid}", status_code=status.HTTP_200_OK)
async def delete_patient(uid: int, db: db_dependency):
    
    db_patient = db.query(models.Patient).filter(models.Patient.uid == uid).first()
    
    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    
    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with UID {uid} is already deleted"
        )
    
    
    db_patient.is_deleted = True
    db.commit()
    
    return {"detail": f"Patient with UID {uid} has been marked as deleted"}

# Patients All API Stop Here



# About Appointment All API Start Here
@app.get("/doc/{doc_regno}/appointments/date/{appointment_date}")
async def get_appointments_by_date(doc_regno: str, appointment_date: date, db: Session = Depends(get_db)):
   
    appointments = db.query(models.Appointment) \
        .join(models.Doctor, models.Appointment.doctor_regno == models.Doctor.regno) \
        .options(joinedload(models.Appointment.patient)) \
        .filter(models.Doctor.regno == doc_regno) \
        .filter(cast(models.Appointment.date_time, Date) == appointment_date) \
        .all()

    if not appointments:
        raise HTTPException(status_code=404, detail="No appointments found for the given doctor and date")

    appointments_data = []
    for appointment in appointments:
        patient = appointment.patient
        
        patient_data = {
            "id": patient.id,
            "firstname": patient.firstname,
            "age": patient.age,
            "gender": patient.gender
        }

        appointments_data.append({
            "appointment_id": appointment.id,
            "date_time": appointment.date_time,
            "day": appointment.day,
            "symptoms": appointment.symptoms,
            "status": appointment.status.value, 
            "patient": patient_data  
        })

    return appointments_data



@app.get("/patient/{patient_id}/appointments/date/{appointment_date}")
async def get_appointments_by_date(patient_uid: str, appointment_date: date, db: Session = Depends(get_db)):
   
    appointments = db.query(models.Appointment) \
        .join(models.Patient, models.Appointment.patient_uid == models.Patient.uid) \
        .options(joinedload(models.Appointment.doctor)) \
        .filter(models.Patient.uid == patient_uid) \
        .filter(cast(models.Appointment.date_time, Date) == appointment_date) \
        .all()

    if not appointments:
        raise HTTPException(status_code=404, detail="No appointments found for the given patient and date")

    appointments_data = []
    for appointment in appointments:
        doctor = appointment.doctor
       
        doctor_data = {
            "firstname": doctor.firstname,
            "department": doctor.department
        }

        appointments_data.append({
            "appointment_id": appointment.id,
            "date_time": appointment.date_time,
            "day": appointment.day,
            "symptoms": appointment.symptoms,
            "status": appointment.status.value, 
            "doctor": doctor_data  
        })

    return appointments_data

# About Appointment All API Stop Here



