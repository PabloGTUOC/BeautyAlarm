from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import LogStatus, RoutineKind, TimePeriod, TrackerStatus


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


# --- Accounts (D5a) ---

class User(BaseModel):
    """What the client is told about the signed-in person. No hash, ever."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=100)
    # Length is the only rule. Composition rules push people towards
    # "Password1!" and this is a household app, not a bank.
    password: str = Field(min_length=10, max_length=200)

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("that does not look like an email address")
        return cleaned


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class AuthConfig(BaseModel):
    allow_registration: bool


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

def _check_kind_fields(
    kind: RoutineKind,
    days_of_week: Optional[List[int]],
    time_period: Optional[TimePeriod],
    target_interval_days: Optional[int],
) -> None:
    """Enforce the per-kind field rules from D11.

    A scheduled routine is defined by its weekdays and slot; a tracked one by
    its interval. Supplying the other kind's fields is a 422 rather than a
    silently ignored value, because silently ignoring a weekday list on a
    haircut would leave the user believing they had set a schedule.
    """
    if kind is RoutineKind.scheduled:
        if days_of_week is None:
            raise ValueError("days_of_week is required for a scheduled routine")
        if time_period is None:
            raise ValueError("time_period is required for a scheduled routine")
        if target_interval_days is not None:
            raise ValueError(
                "target_interval_days applies to tracked routines only"
            )
    else:
        if target_interval_days is None:
            raise ValueError("target_interval_days is required for a tracked routine")
        if days_of_week is not None:
            raise ValueError(
                "days_of_week applies to scheduled routines only — a tracked "
                "routine recurs on an interval, not on weekdays"
            )
        if time_period is not None:
            raise ValueError("time_period applies to scheduled routines only")


class RoutineBase(BaseModel):
    # Required for every routine: with 0 or 3 products there is no single
    # product name to borrow (D8a).
    name: str = Field(min_length=1, max_length=255)
    kind: RoutineKind = RoutineKind.scheduled
    days_of_week: Optional[List[int]] = None
    time_period: Optional[TimePeriod] = None
    target_interval_days: Optional[int] = Field(default=None, ge=1, le=3650)
    start_date: Optional[date] = None
    notification_time: Optional[time] = None
    is_active: bool = True
    end_date: Optional[date] = None

    @field_validator("days_of_week")
    @classmethod
    def check_days(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        return None if value is None else _normalise_days(value)

    @model_validator(mode="after")
    def check_kind(self) -> "RoutineBase":
        _check_kind_fields(
            self.kind, self.days_of_week, self.time_period, self.target_interval_days
        )
        return self


class RoutineCreate(RoutineBase):
    # Ordered: position 0 is applied first (D8a). Empty means an action or
    # service with no products, such as a haircut.
    product_ids: List[int] = Field(default_factory=list)

    @field_validator("product_ids")
    @classmethod
    def check_products(cls, value: List[int]) -> List[int]:
        if len(set(value)) != len(value):
            raise ValueError("product_ids must not repeat a product")
        return value


class RoutineUpdate(BaseModel):
    """Every field optional. Kind coherence is re-checked against the merged
    result in the router, since a patch alone cannot see the stored kind."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    kind: Optional[RoutineKind] = None
    days_of_week: Optional[List[int]] = None
    time_period: Optional[TimePeriod] = None
    target_interval_days: Optional[int] = Field(default=None, ge=1, le=3650)
    start_date: Optional[date] = None
    notification_time: Optional[time] = None
    is_active: Optional[bool] = None
    end_date: Optional[date] = None
    product_ids: Optional[List[int]] = None

    @field_validator("days_of_week")
    @classmethod
    def check_days(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        return None if value is None else _normalise_days(value)

    @field_validator("product_ids")
    @classmethod
    def check_products(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("product_ids must not repeat a product")
        return value


class Routine(RoutineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # In application order. Empty for a tracked service (D8a).
    products: List[Product] = Field(default_factory=list)


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


class TrackingEntry(BaseModel):
    """A tracked routine's elapsed-time state (D11).

    ``days_since`` counts from the last completed log, or from ``start_date``
    when there is none. It is null only when the routine has neither, in which
    case the client shows "not yet recorded" rather than a number.
    """

    routine: Routine
    last_completed: Optional[date] = None
    days_since: Optional[int] = None
    # Three states, not a boolean: the day the target is reached is the day to
    # act, not the day you are late (D11).
    status: TrackerStatus = TrackerStatus.waiting


class TodayResponse(BaseModel):
    date: date
    entries: List[TodayEntry]
    # Always present, not only when something is overdue.
    tracking: List[TrackingEntry] = Field(default_factory=list)


class CalendarDay(BaseModel):
    date: date
    due: int
    completed: int
    skipped: int


class StreakResponse(BaseModel):
    current: int
    longest: int


class RoutineAdherence(BaseModel):
    routine_id: int
    # The routine's own name (D8a). Was the product name, which no longer
    # identifies a routine that holds three products or none.
    routine_name: str
    due: int
    completed: int


# --- Web Push ---

class PushPublicKey(BaseModel):
    public_key: str


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscriptionCreate(BaseModel):
    """Shaped like the browser's PushSubscription.toJSON()."""

    endpoint: str = Field(min_length=1, max_length=500)
    keys: PushKeys


class PushEndpoint(BaseModel):
    endpoint: str = Field(min_length=1, max_length=500)


class PushSubscription(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    endpoint: str


class PushResult(BaseModel):
    delivered: int
