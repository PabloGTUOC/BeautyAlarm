from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .database import engine, get_db

app = FastAPI(title="Beauty Routine Tracker API")

# Allow the Flutter web dev server (any localhost port) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Beauty Routine Tracker API"}

# Products
@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Product).offset(skip).limit(limit).all()

# Routines
@app.post("/routines/", response_model=schemas.Routine)
def create_routine(routine: schemas.RoutineCreate, db: Session = Depends(get_db)):
    db_routine = models.Routine(**routine.model_dump())
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    return db_routine

@app.get("/routines/", response_model=List[schemas.Routine])
def read_routines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Routine).offset(skip).limit(limit).all()

# Daily Logs
@app.post("/logs/", response_model=schemas.DailyLog)
def create_log(log: schemas.DailyLogCreate, db: Session = Depends(get_db)):
    db_log = models.DailyLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@app.get("/logs/", response_model=List[schemas.DailyLog])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.DailyLog).offset(skip).limit(limit).all()
