"""Phase 2 schema: constraints, lifecycle fields, local log dates

Closes G12 (nullable columns), G14 (duplicate logs) and part of G8 by giving the
API the columns its endpoints need.

Not safe against a database holding rows that violate the new constraints: it
makes routines.product_id and daily_logs.* NOT NULL, converts notification_time
from VARCHAR(10) to TIME, and adds UNIQUE(routine_id, log_date). A deployment
with existing data should be inspected before running this.

The log_date backfill derives the local date from the stored UTC timestamp,
which is right for rows written near midday and can be a day off for rows
written near midnight. Only pre-Phase-2 rows are affected; everything written
afterwards carries a real local date.

Revision ID: b2f1c4d7e9a3
Revises: 3569a2e8b447
Create Date: 2026-09-21 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2f1c4d7e9a3'
down_revision: Union[str, None] = '3569a2e8b447'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIME_PERIOD = sa.Enum('morning', 'night', name='timeperiod')
LOG_STATUS = sa.Enum('completed', 'skipped', name='logstatus')


def _replace_foreign_key(table: str, column: str, referent: str, name: str, ondelete: str) -> None:
    """Re-create a foreign key with an ON DELETE rule, finding the old one by reflection.

    The initial migration created unnamed foreign keys, so the server-generated
    name has to be discovered rather than guessed. SQLite is skipped: it does not
    support ALTER for constraints, and does not enforce foreign keys by default,
    so the ORM-level cascade is what actually runs there.
    """
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return
    for fk in sa.inspect(bind).get_foreign_keys(table):
        if fk.get('name') and fk['constrained_columns'] == [column]:
            op.drop_constraint(fk['name'], table, type_='foreignkey')
    op.create_foreign_key(name, table, referent, [column], ['id'], ondelete=ondelete)


def upgrade() -> None:
    with op.batch_alter_table('products') as batch:
        batch.alter_column('name', existing_type=sa.String(length=255), nullable=False)
        batch.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('routines') as batch:
        batch.add_column(
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1'))
        )
        batch.add_column(sa.Column('end_date', sa.Date(), nullable=True))
        batch.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch.alter_column('product_id', existing_type=sa.Integer(), nullable=False)
        batch.alter_column('days_of_week', existing_type=sa.JSON(), nullable=False)
        batch.alter_column('time_period', existing_type=TIME_PERIOD, nullable=False)
        batch.alter_column(
            'notification_time',
            existing_type=sa.String(length=10),
            type_=sa.Time(),
            existing_nullable=True,
        )

    with op.batch_alter_table('daily_logs') as batch:
        batch.add_column(sa.Column('log_date', sa.Date(), nullable=True))
        batch.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    op.execute('UPDATE daily_logs SET log_date = DATE(timestamp) WHERE log_date IS NULL')

    with op.batch_alter_table('daily_logs') as batch:
        batch.alter_column('log_date', existing_type=sa.Date(), nullable=False)
        batch.alter_column('routine_id', existing_type=sa.Integer(), nullable=False)
        batch.alter_column('timestamp', existing_type=sa.DateTime(), nullable=False)
        batch.alter_column('status', existing_type=LOG_STATUS, nullable=False)
        batch.create_unique_constraint('uq_daily_logs_routine_date', ['routine_id', 'log_date'])

    op.create_index(op.f('ix_daily_logs_log_date'), 'daily_logs', ['log_date'], unique=False)

    _replace_foreign_key('routines', 'product_id', 'products', 'fk_routines_product_id', 'RESTRICT')
    _replace_foreign_key('daily_logs', 'routine_id', 'routines', 'fk_daily_logs_routine_id', 'CASCADE')


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.drop_constraint('fk_daily_logs_routine_id', 'daily_logs', type_='foreignkey')
        op.create_foreign_key(None, 'daily_logs', 'routines', ['routine_id'], ['id'])
        op.drop_constraint('fk_routines_product_id', 'routines', type_='foreignkey')
        op.create_foreign_key(None, 'routines', 'products', ['product_id'], ['id'])

    op.drop_index(op.f('ix_daily_logs_log_date'), table_name='daily_logs')

    with op.batch_alter_table('daily_logs') as batch:
        batch.drop_constraint('uq_daily_logs_routine_date', type_='unique')
        batch.alter_column('status', existing_type=LOG_STATUS, nullable=True)
        batch.alter_column('timestamp', existing_type=sa.DateTime(), nullable=True)
        batch.alter_column('routine_id', existing_type=sa.Integer(), nullable=True)
        batch.drop_column('user_id')
        batch.drop_column('log_date')

    with op.batch_alter_table('routines') as batch:
        batch.alter_column(
            'notification_time',
            existing_type=sa.Time(),
            type_=sa.String(length=10),
            existing_nullable=True,
        )
        batch.alter_column('time_period', existing_type=TIME_PERIOD, nullable=True)
        batch.alter_column('days_of_week', existing_type=sa.JSON(), nullable=True)
        batch.alter_column('product_id', existing_type=sa.Integer(), nullable=True)
        batch.drop_column('user_id')
        batch.drop_column('end_date')
        batch.drop_column('is_active')

    with op.batch_alter_table('products') as batch:
        batch.drop_column('user_id')
        batch.drop_column('archived_at')
        batch.alter_column('name', existing_type=sa.String(length=255), nullable=True)
