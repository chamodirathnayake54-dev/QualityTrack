"""Alembic environment with no dotenv loading or connection logging."""

import os

from alembic import context
from sqlalchemy import create_engine

from qualitytrack.models import Base

config = context.config
target_metadata = Base.metadata


def _run():
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("Migration database configuration unavailable")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


_run()
