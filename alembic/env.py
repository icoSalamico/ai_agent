import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from database import Base  # noqa
from database import Company, Conversation
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Get the DATABASE_URL and strip async driver
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not set in .env")

sync_url = database_url.replace("+asyncpg", "")

# Alembic Config object
config = context.config

# Set the correct sync database URL
config.set_main_option("sqlalchemy.url", sync_url)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set metadata for autogenerate
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
