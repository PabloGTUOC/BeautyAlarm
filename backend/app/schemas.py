from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import LogStatus, TimePeriod


def _normalise_days(value: List[int]) -> List[int]:
    """ISO weekdays, sorted and deduplicated (D2, D3)."""
    if not value:
        raise ValueError("days_of_week must list at least one day")
    for day in value:
        if day < 1 or day > 7:
            raise ValueError(
                "days_of_week values must be ISO weekdays 1-7 (1=Monday, 7=Sunday)"
            )
    return sorted(set(value))


# --- Products ---

class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    archived_at: Optional[datetime] = None


# --- Routines ---

class RoutineBase(BaseModel):
    product_id: int
    days_of_week: List[int]
    time_period: TimePeriod
    notification_time: Optional[time] = None
    is_active: bool = True
    end_date: Optional[date] = None

    @field_validator("days_of_week")
    @classmethod
    def check_days(cls, value: List[int]) -> List[int]:
        return _normalise_days(value)


class RoutineCreate(RoutineBase):
    pass


class RoutineUpdate(BaseModel):
    product_id: Optional[int] = None
    days_of_week: Optional[List[int]] = None
    time_period: Optional[TimePeriod] = None
    notification_time: Optional[time] = None
    is_active: Optional[bool] = None
    end_date: Optional[date] = None

    @field_validator("days_of_week")
    @classmethod
    def check_days(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        return None if value is None else _normalise_days(value)


class Routine(RoutineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: Optional[Product] = None


# --- Daily logs ---

class DailyLogCreate(BaseModel):
    routine_id: int
    status: LogStatus
    # Both default server-side: log_date to today in APP_TIMEZONE, timestamp to
    # now in UTC. A client that knows better may override them.
    log_date: Optional[date] = None
    timestamp: Optional[datetime] = None


class DailyLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    routine_id: int
    log_date: date
    timestamp: datetime
    status: LogStatus


# --- Derived views ---

class TodayEntry(BaseModel):
    """A routine due today, with its log if one exists. No log means pending (D6)."""

    routine: Routine
    log: Optional[DailyLog] = None


class TodayResponse(BaseModel):
    date: date
    entries: List[TodayEntry]


class CalendarDay(BaseModel):
    date: date
    due: int
    completed: int
    skipped: int


class StreakResponse(BaseModel):
    current: int
    longest: int
