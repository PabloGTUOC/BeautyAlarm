from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .models import TimePeriod, LogStatus

# Product Schemas
class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    notes: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True

# Routine Schemas
class RoutineBase(BaseModel):
    product_id: int
    days_of_week: List[int]
    time_period: TimePeriod
    notification_time: Optional[str] = None

class RoutineCreate(RoutineBase):
    pass

class Routine(RoutineBase):
    id: int
    product: Optional[Product] = None

    class Config:
        from_attributes = True

# DailyLog Schemas
class DailyLogBase(BaseModel):
    routine_id: int
    timestamp: datetime
    status: LogStatus

class DailyLogCreate(DailyLogBase):
    pass

class DailyLog(DailyLogBase):
    id: int

    class Config:
        from_attributes = True
