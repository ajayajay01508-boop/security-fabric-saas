# Alembic Environment Configuration
# Run from apps/api-gateway/
# Usage:
#   alembic revision --autogenerate -m "description"
#   alembic upgrade head
#   alembic downgrade -1

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
import asyncio

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic detects them
from app.database import Base
from app.models import user, alert, subscription  # noqa: F401

target_metadata = Base.metadata


def get_url():
    import os
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://fabric:fabric_secret@localhost:5432/security_fabric"
    )


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
