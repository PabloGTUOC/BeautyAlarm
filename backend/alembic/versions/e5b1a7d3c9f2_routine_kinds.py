"""Routine kinds, required names, and start dates

Adds the `tracked` routine kind (D11, gap G32): things measured by elapsed days
rather than a weekday schedule, such as a haircut. Adds the required `name`
every routine now needs, because a routine may hold three products or none and
has nothing to borrow a label from (D8a, gap G31). Adds `start_date`, which
closes G28 and doubles as the "days since" baseline for a tracked routine that
has never been logged.

`days_of_week` and `time_period` become nullable: they are meaningless for a
tracked routine. The per-kind rules are enforced by the API schema, not by a
CHECK constraint, so a contradiction is a readable 422 rather than an
IntegrityError.

DATA MIGRATION. `name` is backfilled from each routine's first product and its
time period ("Retinol 0.5% — night"); `start_date` from the earliest log the
routine has. `routines` carries no `created_at`, so the first log is the best
available proxy for when the routine started. Routines that have never been
logged keep a NULL start_date, which reads as "no restriction" — inventing
today's date would wrongly hide a genuinely old routine from past-dated history.

Revision ID: e5b1a7d3c9f2
Revises: d4a9f2c1b8e7
Create Date: 2026-09-24 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5b1a7d3c9f2'
down_revision: Union[str, None] = 'd4a9f2c1b8e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROUTINE_KIND = sa.Enum('scheduled', 'tracked', name='routinekind')
TIME_PERIOD = sa.Enum('morning', 'night', name='timeperiod')


def upgrade() -> None:
    bind = op.get_bind()

    # Nullable first so existing rows survive; tightened once backfilled.
    with op.batch_alter_table('routines') as batch:
        batch.add_column(sa.Column('name', sa.String(length=255), nullable=True))
        batch.add_column(
            sa.Column(
                'kind', ROUTINE_KIND, nullable=False, server_default='scheduled'
            )
        )
        batch.add_column(
            sa.Column('target_interval_days', sa.Integer(), nullable=True)
        )
        batch.add_column(sa.Column('start_date', sa.Date(), nullable=True))

    # Backfill in Python rather than SQL: string concatenation is CONCAT() on
    # MySQL and || on SQLite, and this runs on both.
    rows = bind.execute(
        sa.text(
            """
            SELECT r.id, r.time_period, p.name
            FROM routines r
            LEFT JOIN routine_products rp ON rp.routine_id = r.id
            LEFT JOIN products p ON p.id = rp.product_id
            WHERE r.name IS NULL
            ORDER BY r.id, rp.position, rp.id
            """
        )
    ).fetchall()

    seen = set()
    for routine_id, time_period, product_name in rows:
        if routine_id in seen:
            continue  # keep only the first product of each routine
        seen.add(routine_id)
        if product_name and time_period:
            name = f"{product_name} — {time_period}"
        elif product_name:
            name = product_name
        else:
            name = f"Routine {routine_id}"
        bind.execute(
            sa.text("UPDATE routines SET name = :name WHERE id = :id"),
            {"name": name, "id": routine_id},
        )

    # start_date: the earliest day this routine was ever logged (G28).
    op.execute(
        """
        UPDATE routines SET start_date = (
            SELECT MIN(l.log_date) FROM daily_logs l
            WHERE l.routine_id = routines.id
        )
        WHERE start_date IS NULL
        """
    )

    left = bind.execute(
        sa.text("SELECT COUNT(*) FROM routines WHERE name IS NULL")
    ).scalar()
    if left:
        raise RuntimeError(f"{left} routine(s) still have no name after backfill")

    with op.batch_alter_table('routines') as batch:
        batch.alter_column(
            'name', existing_type=sa.String(length=255), nullable=False
        )
        # Meaningless for a tracked routine, so they stop being required.
        batch.alter_column(
            'days_of_week', existing_type=sa.JSON(), nullable=True
        )
        batch.alter_column(
            'time_period', existing_type=TIME_PERIOD, nullable=True
        )


def downgrade() -> None:
    bind = op.get_bind()

    tracked = bind.execute(
        sa.text("SELECT COUNT(*) FROM routines WHERE kind = 'tracked'")
    ).scalar()
    if tracked:
        raise RuntimeError(
            f"{tracked} tracked routine(s) exist and have no weekday schedule to "
            "fall back to. Delete or convert them before downgrading."
        )

    # Any row without a schedule would violate the restored NOT NULL.
    op.execute(
        """
        UPDATE routines SET days_of_week = '[1, 2, 3, 4, 5, 6, 7]'
        WHERE days_of_week IS NULL
        """
    )
    op.execute("UPDATE routines SET time_period = 'morning' WHERE time_period IS NULL")

    with op.batch_alter_table('routines') as batch:
        batch.alter_column(
            'days_of_week', existing_type=sa.JSON(), nullable=False
        )
        batch.alter_column(
            'time_period', existing_type=TIME_PERIOD, nullable=False
        )
        batch.drop_column('start_date')
        batch.drop_column('target_interval_days')
        batch.drop_column('kind')
        batch.drop_column('name')
