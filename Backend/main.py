# Importing dependencies and packages 
from fastapi import FastAPI, HTTPException, Depends, status, Path, Query, Request
from pydantic import BaseModel, field_validator
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
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for all origins (you can restrict this to specific origins later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (or specify a list of domains here)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

models.Base.metadata.create_all(bind=engine)


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
    mobile: int
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

@field_validator('date_of_birth')
def validate_date_of_birth(cls, v):
        # Assuming the format is dd-mm-yyyy, you can parse it into a datetime object
        return datetime.strptime(v, "%d-%m-%Y").date()  # Converting to date object



class PatientLoginRequest(BaseModel):
    mobile: str
    password: str

    class Config:
        arbitrary_types_allowed = True


class AppointmentStatusEnum(str, Enum):
    PENDING = "PENDING"
    CHECKED = "CHECKED"


class Appointment(BaseModel):
    patient_uid: int
    doctor_regno: int
    date: date
    time: str
    day: str
    symptoms: str
    is_deleted: bool = False
    status: Optional[AppointmentStatusEnum] = AppointmentStatusEnum.PENDING


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120


def create_access_token(
    data: dict,
    expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(id: str, token: str) -> dict:
    try:
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    

        token_id = payload.get("id")

        if token_id != id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in again."
            )
        return True

    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def get_token(id: str, req: Request):
    try:
        # print(user_id)
        if "Authorization" not in req.headers:
            raise HTTPException(status_code=401, detail="login again...")
        token = req.headers["Authorization"].split(" ")[1]
        if not token:
            raise HTTPException(status_code=401, detail="login again")

        token_status = verify_token(id, token)
        return token_status
    except HTTPException as e:
        raise e
    except Exception as e:
        raise e


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# API'S Start From here


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
        password_hash=hashed_password,
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor


# Doctor Login
@app.post("/doctor/login/")
async def authenticate_doctor(doctor: DoctorLoginRequest, db: db_dependency):

    db_doctor = (
        db.query(models.Doctor).filter(models.Doctor.mobile == doctor.mobile).first()
    )

    if not db_doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    if db_doctor.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Doctor account is deleted"
        )

    if not verify_password(doctor.password, db_doctor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    access_token = create_access_token(data={"id": str(db_doctor.regno)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "doctor_firstname": db_doctor.firstname + " " + db_doctor.lastname,
    }


# Each Doctors All Apointments
@app.get("/doctor/{id}/appointments", status_code=status.HTTP_200_OK)
async def get_appointments_for_doctor(id: str, db: db_dependency, token: str = Depends(get_token)):

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.doctor_regno == id,
            models.Appointment.is_deleted == False,
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
                "appointment_symptoms": appointment.symptoms,
                "date": appointment.date,
                "time":appointment.time,
                "day": appointment.day,
                "is_deleted": appointment.is_deleted,
                "patient_info": {
                    "patient_name": f"{appointment.patient.firstname} {appointment.patient.lastname}",
                    "patient_uid": appointment.patient.uid,
                    "patient_disease": appointment.patient.disease,
                    "patient_mobile": appointment.patient.mobile_number,
                    "patient_address": appointment.patient.address,
                },
            }
            for appointment in appointments
        ],
    }

    if token is not None:
        return {"doctor_appointments": doctor_appointments, "token": token}

    return {"doctor_appointments": doctor_appointments}


# get single apointment for each doctor
@app.get("/doctor/{id}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def get_single_appointment_for_doctor(id: str, appointment_id: int, db: db_dependency, token: str = Depends(get_token)):

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == id,
            models.Appointment.is_deleted == False,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted",
        )

    patient = appointment.patient
    
    if token is not None:
        return { "doctor_name": f"{doctor.firstname} {doctor.lastname}",
        "regno": doctor.regno,
        "appointment": {
            "appointment_id": appointment.id,
            "appointment_symptoms": appointment.symptoms,
            "date": appointment.date,
            "time": appointment.time,
            "day": appointment.day,
            "is_deleted": appointment.is_deleted,
            "patient_info": {
                "patient_name": f"{appointment.patient.firstname} {appointment.patient.lastname}",
                "patient_uid": appointment.patient.uid,
                "patient_disease": appointment.patient.disease,
                "patient_mobile": appointment.patient.mobile_number,
                "patient_address": appointment.patient.address,
            },
        }, "token": token}
    
    
# Update single apointment
@app.put("/doctor/{id}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def update_appointment_and_patient_disease(id: str, appointment_id: int, updated_data: dict, db: db_dependency, token: str = Depends(get_token)):

    # Fetch the doctor based on the regno
    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    # Fetch the appointment for the given appointment_id
    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == id,
            models.Appointment.is_deleted == False,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted",
        )

    # Update the appointment fields from updated_data
    for key, value in updated_data.items():
        if hasattr(appointment, key) and value is not None:
            setattr(appointment, key, value)

    # If 'disease' is part of the updated_data, update the patient's disease
    if "disease" in updated_data:
        patient = (
            db.query(models.Patient)
            .filter(models.Patient.uid == appointment.patient_uid)
            .first()
        )

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        patient.disease = updated_data["disease"]
        db.commit()
        db.refresh(patient)

    # If 'status' is part of the updated_data, update the appointment's status
    if "status" in updated_data:
        appointment.status = updated_data["status"]
        db.commit()
        db.refresh(appointment)

    # Return the updated appointment and patient data
    return {
        "detail": "Appointment and patient diseases updated successfully",
        "appointment": {
            "appointment_id": appointment.id,
            "date": appointment.date,
            "time": appointment.time,
            "day": appointment.day,
            "status": appointment.status,
            "is_deleted": appointment.is_deleted,
        },
        "patient": {
            "patient_uid": appointment.patient_uid,
            "patient_name": f"{appointment.patient.firstname} {appointment.patient.lastname}",
            "disease": patient.disease if patient else "Not found",
        },
        "token": token
    }


# Add Next Appointment for Patient
@app.post("/doctor/{id}/appointment/{appointment_id}/new", status_code=status.HTTP_201_CREATED)
async def create_new_appointment_for_patient(
    id: str,
    appointment_id: int,
    new_appointment_data: Appointment,  # Expecting an Appointment model (Pydantic schema)
    db: Session = Depends(get_db),
    token: str = Depends(get_token)
):
    # Fetch the doctor based on the regno
    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    # Fetch the current appointment using the appointment_id
    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == id,
            models.Appointment.is_deleted == False,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted",
        )

    # Fetch the patient based on the patient_uid
    patient = db.query(models.Patient).filter(models.Patient.uid == appointment.patient_uid).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Create a new appointment using the Appointment Pydantic model data
    new_appointment = models.Appointment(
        doctor_regno=id,
        patient_uid=patient.uid,
        date=new_appointment_data.date,  # New date from the request
        time=new_appointment_data.time,  # New time from the request
        day=new_appointment_data.day,    # New day from the request
        symptoms=new_appointment_data.symptoms,  # Symptoms from the request
        status=new_appointment_data.status or "PENDING",  # Status default is "PENDING"
        is_deleted=False
    )

    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    # Return the new appointment details
    return {
        "detail": "New appointment created successfully",
        "appointment": {
            "appointment_id": new_appointment.id,
            "date": new_appointment.date,
            "time": new_appointment.time,
            "day": new_appointment.day,
            "status": new_appointment.status,
            "patient_name": f"{patient.firstname} {patient.lastname}",
        },
    }


# Delete each apointment of each doctor
@app.delete("/doctor/{id}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def delete_appointment(id: str, appointment_id: int, db: db_dependency, token: str = Depends(get_token)):

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.doctor_regno == id,
            models.Appointment.is_deleted == False,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted",
        )

    appointment.is_deleted = True
    db.commit()
    db.refresh(appointment)
    
    if token is not None:
      return {
        "detail": f"Appointment with id {appointment_id} has been marked as deleted","token" : token
    }


# Get all patient which are present and get apointments
@app.get("/doctors/{id}/patients/with-appointments", status_code=status.HTTP_200_OK)
async def get_patients_for_doctor_with_appointments(id: str, db: db_dependency, token: str = Depends(get_token)):

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    patients_with_appointments = (
        db.query(models.Patient)
        .join(models.Appointment, models.Appointment.patient_uid == models.Patient.uid)
        .filter(
            models.Appointment.doctor_regno == id,
            models.Appointment.is_deleted == False,
        )
        .group_by(models.Patient.uid)
        .all()
    )

    if not patients_with_appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients with appointments found for this doctor",
        )
        
    if token is not None:

        return [
            {
                "patient_uid": patient.uid,
                "patient_name": f"{patient.firstname} {patient.lastname}",
                "patient_disease":patient.disease,
                "appointments": [
                    {
                        "appointment_id": appointment.id,
                        "date": appointment.date,
                        "time":appointment.time,
                        "symptoms":appointment.symptoms,
                        "status": appointment.status,
                        "is_deleted": appointment.is_deleted,
                    }
                    for appointment in patient.appointments
                    if appointment.doctor_regno == id and appointment.is_deleted == False
                ],"token" : token
            }
            for patient in patients_with_appointments
        ]
       

# Get Doctor Profile
@app.get("/doctor/{id}/profile", status_code=status.HTTP_200_OK)
async def get_doctor_profile(id: str, db: db_dependency, token: str = Depends(get_token)):

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == id, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )
        
    if token is not None:

        return {
            "doctor_profile": {
                "regno": doctor.regno,
                "doctor_name": f"{doctor.firstname} {doctor.lastname}",
                "department": doctor.department,
                "mobile": doctor.mobile,
            },"token" : token
        }


# Update Doctor Profile
@app.put("/doctor/{id}", status_code=status.HTTP_200_OK)
async def update_doctor(id: str, updated_data: dict, db: db_dependency, token: str = Depends(get_token)):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.regno == id).first()

    if not db_doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    if db_doctor.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor account is deleted and cannot be updated",
        )

    # Loop through the updated data and apply changes to the database model
    for key, value in updated_data.items():
        if hasattr(db_doctor, key) and value is not None:
            setattr(db_doctor, key, value)

    db.commit()
    db.refresh(db_doctor)
    
    if token is not None:
        return {
            "detail": f"Doctor with regno {id} updated successfully",
            "updated_data": {
                "regno": db_doctor.regno,
                "doctor_name": f"{db_doctor.firstname} {db_doctor.lastname}",
                "department": db_doctor.department,
                "mobile": db_doctor.mobile
            },
            "token": token
        }

# Delete doctor
@app.delete("/doctor/{id}", status_code=status.HTTP_200_OK)
async def delete_doctor(id: str, db: db_dependency, token: str = Depends(get_token)):
   
    db_doctor = db.query(models.Doctor).filter(models.Doctor.regno == id).first()

   
    if not db_doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

   
    if db_doctor.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor is already deleted"
        )

    
    db_doctor.is_deleted = True
    db.commit()

    if token is not None:
        return {
            "detail": f"Doctor with regno {id} has been marked as deleted",
            "token": token
        }

# Doctors All API Stop Here



# Patients All API Start Here
@app.post("/patient/", status_code=status.HTTP_201_CREATED)
async def add_patient(patient: Patient, db: db_dependency):
    hashed_password = hash_password(patient.password)
    uid = models.generate_unique_uid(db)
    print(Patient)
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
        password_hash=hashed_password,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    print(db_patient)
    return db_patient


# Patient Login
@app.post("/Patient/login/")
async def patient_authenticate(patient: PatientLoginRequest, db: db_dependency):

    db_patient = (
        db.query(models.Patient).filter(models.Patient.mobile_number == patient.mobile).first()
    )

    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account is deleted",
        )

    if not verify_password(patient.password, db_patient.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    access_token = create_access_token(data={"id": str(db_patient.uid)})
    

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "patient_uid": db_patient.uid,
        "patient_name": db_patient.firstname + " " + db_patient.lastname,
    }


@app.post("/patient/{id}/appointments", status_code=status.HTTP_201_CREATED)
async def create_appointment(appointment: Appointment, db: db_dependency, token: str = Depends(get_token)):
    patient = (
        db.query(models.Patient)
        .filter(models.Patient.uid == appointment.patient_uid)
        .first()
    )
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == appointment.doctor_regno)
        .first()
    )
    if not doctor or doctor.is_deleted:  # Access `is_deleted` on the retrieved `doctor` object
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    new_appointment = models.Appointment(
        patient_uid=patient.uid,
        doctor_regno=doctor.regno,
        date=appointment.date,
        time=appointment.time,
        day=appointment.day,
        symptoms=appointment.symptoms,
        status=appointment.status,
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    if token is not None:
        return {
            "id": new_appointment.id,
            "patient_uid": appointment.patient_uid,
            "date": new_appointment.date,
            "time":new_appointment.time,
            "day": new_appointment.day,
            "symptoms": new_appointment.symptoms,
            "status": new_appointment.status.value,
        }


# Get All Apointments of each Patient
@app.get("/patient/{id}/appointments", status_code=status.HTTP_200_OK)
async def get_patient_appointments(id: str, db: db_dependency, token: str = Depends(get_token)):

    db_patient = db.query(models.Patient).filter(models.Patient.uid == id).first()

    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account is deleted",
        )

    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_uid == db_patient.uid,
            models.Appointment.is_deleted == False,
        )
        .all()
    )
    if not appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment Not Yet Created"
        )
    
    # Fetch the doctor's details and include them in the response
    appointments_with_details = []
    for appointment in appointments:
        doctor = db.query(models.Doctor).filter(models.Doctor.regno == appointment.doctor_regno).first()
        if doctor:
            appointment.doctor_name = f"Dr. {doctor.firstname} {doctor.lastname}"  # Combine first name and last name
        
        # Append the appointment details along with appointment_id
        appointments_with_details.append({
            "appointment_id": appointment.id,  # Add the appointment ID
            "doctor_name": appointment.doctor_name,
            "date": appointment.date,
            "time": appointment.time,
            "day": appointment.day,
            "symptoms": appointment.symptoms,
            "status": appointment.status
        })

    if token is not None:
        return {
            "patient_name": f"{db_patient.firstname} {db_patient.lastname}",
            "appointments": appointments_with_details,
            "token": token
        }


# Get Single Appointment of each patient
@app.get("/patient/{id}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def get_single_appointment(id: str, appointment_id: int, db: db_dependency, token: str = Depends(get_token)):
    # Fetch the patient using the patient ID
    db_patient = db.query(models.Patient).filter(models.Patient.uid == id).first()

    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account is deleted",
        )

    # Fetch the appointment using the appointment_id
    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,  # Use 'appointment_id' here
            models.Appointment.patient_uid == db_patient.uid,
            models.Appointment.is_deleted == False,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or has been deleted",
        )

    # Fetch the doctor details related to this appointment
    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == appointment.doctor_regno)
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found for the appointment",
        )

    if token is not None:
        return {
            "patient_name": f"{db_patient.firstname} {db_patient.lastname}",
            "appointment": {
                "id": appointment.id,
                "date": appointment.date,
                "time":appointment.time,
                "day": appointment.day,
                "symptoms":appointment.symptoms,
                "doctor_name": f"{doctor.firstname} {doctor.lastname}",
                "is_deleted": appointment.is_deleted,
            },
            "token": token
        }


# Update Apointment using apointment id
@app.put("/patient/{id}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def update_appointment(
    id: str, 
    appointment_id: int, 
    updated_data: dict, 
    db: db_dependency,  
    token: str = Depends(get_token)
):
    # Retrieve the appointment from the database
    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id)
        .first()
    )

    # Check if the appointment exists
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    # Check if the patient ID matches
    if appointment.patient_uid != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient ID does not match appointment's patient UID",
        )

    # Check if the appointment is deleted (it cannot be updated if deleted)
    if appointment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a deleted appointment",
        )

    # Update all fields in the appointment
    for key, value in updated_data.items():
        if hasattr(appointment, key) and value is not None:
            setattr(appointment, key, value)

    # Commit changes to the database
    db.commit()
    db.refresh(appointment)

    # Return the updated appointment data
    return {
        "detail": f"Appointment with id {appointment_id} updated successfully",
        "updated_data": {
            "id": appointment.id,
            "date": appointment.date,
            "time": appointment.time,
            "day": appointment.day,
            "doctor_regno": appointment.doctor_regno,
            "symptoms": appointment.symptoms,  # Assuming `symptoms` is also a field
            "is_deleted": appointment.is_deleted,
        },
        "token": token,
    }


# Delete or Cancel Apointment
@app.delete("/patient/{id}/appointment/{appointment_id}", status_code=status.HTTP_200_OK)
async def delete_appointment(
    id: str,
    appointment_id: int,
    db: db_dependency,
    token: str = Depends(get_token),
):
    
    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    if appointment.patient_uid != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient ID does not match appointment's patient UID",
        )

    if appointment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Appointment with ID {appointment_id} is already marked as deleted",
        )

   
    appointment.is_deleted = True
    db.commit()

    
    return {
        "detail": f"Appointment with ID {appointment_id} has been marked as deleted",
        "token": token,
    }


# Get all Doctors
@app.get("/patient/{id}/doctors/", status_code=status.HTTP_200_OK)
async def get_all_doctors(db: db_dependency,  token: str = Depends(get_token)):

    doctors = db.query(models.Doctor).filter(models.Doctor.is_deleted == False).all()

    if not doctors:
        return {"detail": "No doctors available"}

    doctor_list = [
        {
            "id": doctor.id,
            "regno": doctor.regno,
            "firstname": doctor.firstname,
            "lastname": doctor.lastname,
            "department": doctor.department,
            "mobile": doctor.mobile,
        }
        for doctor in doctors
    ]

    if token is not None:
        return {"doctors": doctor_list,"token" : token}


# Get single Doctor
@app.get("/patient/{id}/doctor/{regno}", status_code=status.HTTP_200_OK)
async def get_single_doctor(regno: str, db: db_dependency,  token: str = Depends(get_token)):

    doctor = (
        db.query(models.Doctor)
        .filter(models.Doctor.regno == regno, models.Doctor.is_deleted == False)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or has been deleted",
        )

    doctor_details = {
        "regno": doctor.regno,
        "firstname": doctor.firstname,
        "lastname": doctor.lastname,
        "department": doctor.department,
        "mobile": doctor.mobile,
    }

    if token is not None:
        return {"doctor": doctor_details, "token" : token}


# Get Patient Profile
@app.get("/patient/{id}/profile", status_code=status.HTTP_200_OK)
async def get_patient_profile(id: str, db: db_dependency,  token: str = Depends(get_token)):

    patient = (
        db.query(models.Patient)
        .filter(models.Patient.uid == id, models.Patient.is_deleted == False)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or has been deleted",
        )

    patient_profile = {
        "uid": patient.uid,
        "firstname": patient.firstname,
        "lastname": patient.lastname,
        "mobile_number": patient.mobile_number,
        "address": patient.address,
        "date_of_birth": patient.date_of_birth,
    }
    print(patient_profile)
    if token is not None:
        return {"patient": patient_profile, "token" : token}


# Update Patient Informatin
@app.put("/patient/{id}", status_code=status.HTTP_200_OK)
async def update_patient(id: str, updated_data: dict, db: db_dependency,  token: str = Depends(get_token)):

    db_patient = db.query(models.Patient).filter(models.Patient.uid == id).first()

    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account is deleted and cannot be updated",
        )

    for key, value in updated_data.items():
        if hasattr(db_patient, key) and value is not None:
            setattr(db_patient, key, value)

    db.commit()
    db.refresh(db_patient)
    
    if token is not None:
        return {
            "detail": f"Patient with uid {id} updated successfully",
            "updated_data": db_patient,
            "token" : token
        }


# Delete Patient
@app.delete("/patient/{id}", status_code=status.HTTP_200_OK)
async def delete_patient(id: int, db: db_dependency,  token: str = Depends(get_token)):

    db_patient = db.query(models.Patient).filter(models.Patient.uid == id).first()

    if not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    if db_patient.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with UID {id} is already deleted",
        )

    db_patient.is_deleted = True
    db.commit()
    if token is not None:
        return {"detail": f"Patient with UID {id} has been marked as deleted", "token" : token}

# Patients All API Stop Here



# Extra For Filtering
@app.get("/doc/{id}/appointments/date/{appointment_date}")
async def get_appointments_by_date(
    id: str, appointment_date: date, db: db_dependency,  token: str = Depends(get_token)
):

    appointments = (
        db.query(models.Appointment)
        .join(models.Doctor, models.Appointment.doctor_regno == models.Doctor.regno)
        .options(joinedload(models.Appointment.patient))
        .filter(models.Doctor.regno == id)
        .filter(cast(models.Appointment.date, Date) == appointment_date)
        .all()
    )

    if not appointments:
        raise HTTPException(
            status_code=404,
            detail="No appointments found for the given doctor and date",
        )

    appointments_data = []
    for appointment in appointments:
        patient = appointment.patient

        patient_data = {
            "id": patient.id,
            "firstname": patient.firstname,
            "age": patient.age,
            "gender": patient.gender,
        }

        appointments_data.append(
            {
                "appointment_id": appointment.id,
                "date": appointment.date,
                "time": appointment.time,
                "day": appointment.day,
                "symptoms": appointment.symptoms,
                "status": appointment.status.value,
                "patient": patient_data,
            }
        )
        
    if token is not None:
        return {"appointments_data" : appointments_data, "token" : token }



@app.get("/patient/{id}/appointments/date/{appointment_date}")
async def get_appointments_by_date(
    id: str, appointment_date: date, db: db_dependency, token: str = Depends(get_token)
):

    appointments = (
        db.query(models.Appointment)
        .join(models.Patient, models.Appointment.patient_uid == models.Patient.uid)
        .options(joinedload(models.Appointment.doctor))
        .filter(models.Patient.uid == id)
        .filter(cast(models.Appointment.date, Date) == appointment_date)
        .all()
    )

    if not appointments:
        raise HTTPException(
            status_code=404,
            detail="No appointments found for the given patient and date",
        )

    appointments_data = []
    for appointment in appointments:
        doctor = appointment.doctor

        doctor_data = {"firstname": doctor.firstname, "department": doctor.department}

        appointments_data.append(
            {
                "appointment_id": appointment.id,
                "date": appointment.date,
                "day": appointment.day,
                "symptoms": appointment.symptoms,
                "status": appointment.status.value,
                "doctor": doctor_data,
            }
        )
        print(appointments_data)
    if token is not None:
        return {"appointments_data" : appointments_data, "token" : token }


# About Appointment All API Stop Here
