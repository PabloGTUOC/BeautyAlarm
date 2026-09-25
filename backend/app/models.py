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


class RoutineKind(str, enum.Enum):
    """How a routine's due-ness is decided (D11).

    ``scheduled`` recurs on ISO weekdays. ``tracked`` has no weekday schedule at
    all: it is measured by the days elapsed since its last completed log against
    ``target_interval_days``, and is excluded from streaks and adherence (D12).
    """

    scheduled = "scheduled"
    tracked = "tracked"


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

    # Membership rows, not routines: a product reaches its routines through the
    # join table so the ordering lives in one place (D8a).
    routine_links = relationship("RoutineProduct", back_populates="product")


class RoutineProduct(Base):
    """Ordered membership of a product in a routine (D8a).

    ``position`` is deliberately not unique: enforcing it would make reordering
    require temporary values to dodge the constraint, for no benefit. Read the
    rows with ``ORDER BY position, id`` and the order is stable regardless.
    """

    __tablename__ = "routine_products"
    __table_args__ = (
        UniqueConstraint(
            "routine_id", "product_id", name="uq_routine_products_routine_product"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(
        Integer, ForeignKey("routines.id", ondelete="CASCADE"), nullable=False
    )
    # RESTRICT: a product in use by any routine cannot be hard-deleted. Archiving
    # is the supported way to retire one.
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    position = Column(Integer, nullable=False, default=0)

    routine = relationship("Routine", back_populates="product_links")
    product = relationship("Product", back_populates="routine_links")


class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    # Required: a routine can no longer borrow a label from a single product,
    # because it may have three products or none (D8a).
    name = Column(String(255), nullable=False)
    kind = Column(
        Enum(RoutineKind),
        nullable=False,
        default=RoutineKind.scheduled,
        server_default=RoutineKind.scheduled.value,
    )
    # ISO weekdays, 1=Monday..7=Sunday (D2). Sorted and deduplicated by the schema.
    # Required when scheduled, null when tracked (D11) — the schema enforces it.
    days_of_week = Column(JSON, nullable=True)
    # Display bucket only — never a trigger (specs.md section 4). Null when tracked.
    time_period = Column(Enum(TimePeriod), nullable=True)
    # Required when tracked, null when scheduled (D11). Days between occurrences.
    target_interval_days = Column(Integer, nullable=True)
    # Not due before this local date (G28). Also the "days since" baseline for a
    # tracked routine that has never been logged.
    start_date = Column(Date, nullable=True)
    # The only trigger source. Null means this routine raises no notification.
    notification_time = Column(Time, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=sa.text("1"))
    end_date = Column(Date, nullable=True)
    user_id = Column(Integer, nullable=True)

    product_links = relationship(
        "RoutineProduct",
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineProduct.position, RoutineProduct.id",
    )
    # No passive_deletes: SQLAlchemy removes the logs itself, so deletion behaves
    # the same whether or not the database enforces the foreign key.
    logs = relationship(
        "DailyLog", back_populates="routine", cascade="all, delete-orphan"
    )

    @property
    def products(self):
        """The routine's products in application order (D8a).

        Empty for an action or service such as a haircut, which has no products.
        """
        return [link.product for link in self.product_links]


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
