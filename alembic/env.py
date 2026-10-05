import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context
from app.models import Base

# ============================================================
# Load environment variables
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("MIGRATION_DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


# ============================================================
# Alembic Config
# ============================================================

# Alembic 的 Config object
config = context.config


# ============================================================
# Logging
# ============================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# SQLAlchemy Models
# ============================================================

# Base.metadata 包含所有 SQLAlchemy Model 的 Table 定義。
#
# Alembic autogenerate 會拿這份 metadata
# 跟 PostgreSQL 目前的 schema 比較。
target_metadata = Base.metadata


# ============================================================
# Offline migration
# ============================================================


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode.

    Offline mode 不建立真正的 DB connection，
    而是根據 DATABASE_URL 產生 migration SQL。
    """

    url = DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# Online migration
# ============================================================


def run_migrations_online() -> None:
    """
    Run migrations in online mode.

    Online mode 會真的連接 PostgreSQL
    然後執行 Alembic migration。
    """

    connectable = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================
# Entry point
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
