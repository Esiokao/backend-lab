# tests/database.py

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models import Base

# Load environment variables from .env.
load_dotenv()

# Get the test database URL.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set")


# Create the SQLAlchemy engine for the test database.
engine = create_engine(
    TEST_DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)


# Create the Session factory for the test database.
SessionLocal = sessionmaker(bind=engine)


def get_db():
    # Create a database session for tests.
    with SessionLocal() as session:
        # Provide the session to the caller.
        yield session


def check_database_connection() -> None:
    # Check whether PostgreSQL accepts a query.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


# Create tables in the test database.
Base.metadata.create_all(engine)
