import enum

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

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
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=True)
    notes = Column(String(1000), nullable=True)
    # Soft delete: archived products keep their history and drop out of pickers.
    archived_at = Column(DateTime, nullable=True)
    # Reserved for multi-user (D4). Unused in v1.
    user_id = Column(Integer, nullable=True)

    routines = relationship("Routine", back_populates="product")


class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    # ISO weekdays, 1=Monday..7=Sunday (D2). Sorted and deduplicated by the schema.
    days_of_week = Column(JSON, nullable=False)
    # Display bucket only — never a trigger (specs.md section 4).
    time_period = Column(Enum(TimePeriod), nullable=False)
    # The only trigger source. Null means this routine raises no notification.
    notification_time = Column(Time, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=sa.text("1"))
    end_date = Column(Date, nullable=True)
    user_id = Column(Integer, nullable=True)

    product = relationship("Product", back_populates="routines")
    # No passive_deletes: SQLAlchemy removes the logs itself, so deletion behaves
    # the same whether or not the database enforces the foreign key.
    logs = relationship(
        "DailyLog", back_populates="routine", cascade="all, delete-orphan"
    )


class DailyLog(Base):
    __tablename__ = "daily_logs"
    __table_args__ = (
        UniqueConstraint("routine_id", "log_date", name="uq_daily_logs_routine_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(
        Integer, ForeignKey("routines.id", ondelete="CASCADE"), nullable=False
    )
    # Local calendar date per APP_TIMEZONE (specs.md section 4). This, not the UTC
    # timestamp, is what "today", uniqueness and streaks are computed on.
    log_date = Column(Date, nullable=False, index=True)
    # UTC instant the user acted.
    timestamp = Column(DateTime, nullable=False)
    status = Column(Enum(LogStatus), nullable=False)
    user_id = Column(Integer, nullable=True)

    routine = relationship("Routine", back_populates="logs")


class PushSubscription(Base):
    """A browser's Web Push endpoint (D1b). One row per installed client."""

    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(500), nullable=False, unique=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    # Set when a send fails transiently. A 404 or 410 deletes the row instead:
    # the browser has thrown the subscription away and it will never work again.
    last_failure_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, nullable=True)
