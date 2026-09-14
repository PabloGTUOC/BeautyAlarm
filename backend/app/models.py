from sqlalchemy import Column, Integer, String, Enum, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import enum
from .database import Base

class TimePeriod(str, enum.Enum):
    morning = "morning"
    night = "night"

class LogStatus(str, enum.Enum):
    completed = "completed"
    skipped = "skipped"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    brand = Column(String(255), nullable=True)
    notes = Column(String(1000), nullable=True)

    routines = relationship("Routine", back_populates="product")

class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    days_of_week = Column(JSON) # e.g., [1, 2, 3, 4, 5, 6, 7] for Mon-Sun
    time_period = Column(Enum(TimePeriod))
    notification_time = Column(String(10), nullable=True) # e.g., "08:00"

    product = relationship("Product", back_populates="routines")
    logs = relationship("DailyLog", back_populates="routine")

class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(Integer, ForeignKey("routines.id"))
    timestamp = Column(DateTime)
    status = Column(Enum(LogStatus))

    routine = relationship("Routine", back_populates="logs")
