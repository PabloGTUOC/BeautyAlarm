"""Routines hold many ordered products

Replaces the single `routines.product_id` with a `routine_products` join table
carrying an explicit `position`, so one routine can be hyaluronic acid, then
peptides, then moisturiser (D8a, gap G30). A routine with no rows here is an
action or service rather than a product application.

DATA MIGRATION. Every existing routine is backfilled as a one-product routine at
position 0 before `product_id` is dropped.

The downgrade can only restore `product_id` while every routine has at most one
product, and none has zero. It raises rather than silently discarding products.

Revision ID: d4a9f2c1b8e7
Revises: c7d3e81f5b20
Create Date: 2026-09-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4a9f2c1b8e7'
down_revision: Union[str, None] = 'c7d3e81f5b20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_product_fk() -> None:
    """Drop the foreign key on routines.product_id, whatever it is called.

    MySQL refuses to drop a column an index-backed foreign key depends on.
    SQLite is skipped: batch_alter_table rebuilds the table without the column,
    so there is no constraint to drop first.
    """
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return
    for fk in sa.inspect(bind).get_foreign_keys('routines'):
        if fk.get('name') and fk['constrained_columns'] == ['product_id']:
            op.drop_constraint(fk['name'], 'routines', type_='foreignkey')


def upgrade() -> None:
    op.create_table(
        'routine_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('routine_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        # Application order. Not unique per routine on purpose: a unique index
        # would force temporary values when reordering, for no benefit.
        sa.Column('position', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['routine_id'], ['routines.id'],
            name='fk_routine_products_routine_id', ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['product_id'], ['products.id'],
            name='fk_routine_products_product_id', ondelete='RESTRICT',
        ),
        sa.UniqueConstraint(
            'routine_id', 'product_id', name='uq_routine_products_routine_product'
        ),
    )
    op.create_index(
        op.f('ix_routine_products_id'), 'routine_products', ['id'], unique=False
    )

    # Backfill before dropping the column it reads from. Portable to both
    # SQLite and MySQL.
    op.execute(
        """
        INSERT INTO routine_products (routine_id, product_id, position)
        SELECT id, product_id, 0 FROM routines
        """
    )

    _drop_product_fk()
    with op.batch_alter_table('routines') as batch:
        batch.drop_column('product_id')


def downgrade() -> None:
    bind = op.get_bind()

    multi = bind.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM (
                SELECT routine_id FROM routine_products
                GROUP BY routine_id HAVING COUNT(*) > 1
            ) AS t
            """
        )
    ).scalar()
    if multi:
        raise RuntimeError(
            f"{multi} routine(s) have more than one product; downgrading would "
            "discard products. Reduce them to one product each first."
        )

    # Nullable first: existing rows have nothing to put in it yet. No table
    # alias in the UPDATE — SQLite does not accept one.
    with op.batch_alter_table('routines') as batch:
        batch.add_column(sa.Column('product_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE routines SET product_id = (
            SELECT rp.product_id FROM routine_products rp
            WHERE rp.routine_id = routines.id
        )
        """
    )

    # A routine with no products (a tracked service) cannot round-trip: there is
    # no product to point at and the column is NOT NULL.
    orphans = bind.execute(
        sa.text("SELECT COUNT(*) FROM routines WHERE product_id IS NULL")
    ).scalar()
    if orphans:
        raise RuntimeError(
            f"{orphans} routine(s) have no products and cannot be represented by "
            "a NOT NULL product_id. Delete them or give them a product first."
        )

    with op.batch_alter_table('routines') as batch:
        batch.alter_column(
            'product_id', existing_type=sa.Integer(), nullable=False
        )
    if bind.dialect.name != 'sqlite':
        op.create_foreign_key(
            'fk_routines_product_id', 'routines', 'products',
            ['product_id'], ['id'], ondelete='RESTRICT',
        )

    op.drop_index(op.f('ix_routine_products_id'), table_name='routine_products')
    op.drop_table('routine_products')
