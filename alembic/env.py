import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context
from app.models import Base

# Load environment variables from the project .env file.
load_dotenv()

# Read the optional target from Alembic's -x argument.
# Example: alembic -x db=test upgrade head
db_target = context.get_x_argument(as_dictionary=True).get("db")

# Select the connection URL without changing the existing environment variables.
if db_target == "test":
    # Use the admin connection to prepare the test database schema.
    MIGRATION_DATABASE_URL = os.getenv("TEST_ADMIN_DATABASE_URL")
elif db_target is None or db_target == "dev":
    # Keep the default behavior for development migrations.
    MIGRATION_DATABASE_URL = os.getenv("MIGRATION_DATABASE_URL")
else:
    # Reject unknown targets to avoid migrating an unintended database.
    raise ValueError(f"Unsupported migration target: {db_target}")

# Fail early if the selected database URL is missing.
if not MIGRATION_DATABASE_URL:
    raise RuntimeError("Migration database URL is not set")

config = context.config

# Load Alembic's logging configuration.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use SQLAlchemy models as the metadata for migration autogeneration.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without opening a database connection."""
    context.configure(
        url=MIGRATION_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the selected database."""
    # Avoid keeping a persistent connection pool for this migration process.
    connectable = create_engine(
        MIGRATION_DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    # Release the engine's resources after the migration completes.
    connectable.dispose()


# Choose SQL generation or live database execution based on Alembic's mode.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
