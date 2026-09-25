"""Household accounts: users, sessions, and owned rows

Creates the `users` and `sessions` tables (D4a, D5a) and turns the reserved
`user_id` columns into real foreign keys. D4 put those columns on every table in
Phase 2 precisely so this would be additive, and it is: no column is added to a
domain table here, only constrained.

`user_id` stays NULLABLE, deliberately. Rows written before Phase 9 belong to
nobody, and on a fresh upgrade there is no account to assign them to yet. A
migration that demanded NOT NULL here would fail inside `alembic upgrade head`,
which the container runs on boot, so the API could not start; and it could not
start until somebody registered, which they could not do while it was down.

Ownership is enforced in the application instead: every write sets `user_id` and
every read filters on it, so an unowned row is invisible and unreachable rather
than shared. Claim pre-Phase-9 rows with

    docker compose exec api python scripts/create_user.py --adopt-to you@example.com

Tightening the columns to NOT NULL is left to a later revision, once real
deployments have adopted their rows (PLAN.md G46).

Revision ID: a7e2d64c1b93
Revises: e5b1a7d3c9f2
Create Date: 2026-09-25 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7e2d64c1b93'
down_revision: Union[str, None] = 'e5b1a7d3c9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every domain table that gains an owner.
OWNED = ('products', 'routines', 'daily_logs', 'push_subscriptions')


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        # argon2id output, comfortably inside 255 chars.
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)

    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        # SHA-256 hex. The raw token lives only in the cookie.
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], name='fk_sessions_user_id', ondelete='CASCADE'
        ),
        sa.UniqueConstraint('token_hash', name='uq_sessions_token_hash'),
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index(
        op.f('ix_sessions_token_hash'), 'sessions', ['token_hash'], unique=False
    )

    # The columns already exist (D4); this only indexes and constrains them.
    # SQLite cannot add a foreign key to an existing column without rebuilding
    # the table, and it does not enforce them by default anyway, so the ORM-level
    # scoping is what actually runs there.
    bind = op.get_bind()
    for table in OWNED:
        op.create_index(f'ix_{table}_user_id', table, ['user_id'], unique=False)
        if bind.dialect.name != 'sqlite':
            op.create_foreign_key(
                f'fk_{table}_user_id', table, 'users',
                ['user_id'], ['id'], ondelete='CASCADE',
            )


def downgrade() -> None:
    bind = op.get_bind()
    for table in OWNED:
        if bind.dialect.name != 'sqlite':
            op.drop_constraint(f'fk_{table}_user_id', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_user_id', table_name=table)

    op.drop_index(op.f('ix_sessions_token_hash'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
