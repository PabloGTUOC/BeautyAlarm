import os
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa

from app.database import Base

BACKEND = Path(__file__).resolve().parent.parent


def test_migrations_produce_the_model_schema(tmp_path):
    """alembic upgrade head must match what the models declare.

    Guards the failure mode where a model gains a column and the migration does
    not, which only shows up in production as a missing-column error.
    """
    db = tmp_path / "migrated.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    result = subprocess.run(
        # -m alembic rather than the bare binary: the test must not depend on
        # the virtualenv being on PATH.
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    inspector = sa.inspect(sa.create_engine(f"sqlite:///{db}"))
    for table in Base.metadata.sorted_tables:
        assert table.name in inspector.get_table_names()
        migrated = {c["name"] for c in inspector.get_columns(table.name)}
        declared = {c.name for c in table.columns}
        assert declared == migrated, f"{table.name}: models {declared}, migration {migrated}"
