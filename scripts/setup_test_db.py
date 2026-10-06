"""Set up the PostgreSQL test database and runtime role."""

import os

import psycopg
from dotenv import load_dotenv
from psycopg import sql

# Load local .env configuration.
load_dotenv()

ADMIN_URL = os.environ["ADMIN_DATABASE_URL"]
TEST_ADMIN_DATABASE_URL = os.environ["TEST_ADMIN_DATABASE_URL"]
TEST_DB = os.environ["TEST_DATABASE_NAME"]
TEST_USER = os.environ["TEST_DATABASE_USER"]
TEST_PASSWORD = os.environ["TEST_DATABASE_PASSWORD"]


def database_exists(conn, database_name: str) -> bool:
    """Check whether the database already exists."""
    result = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (database_name,),
    )
    return result.fetchone() is not None


def role_exists(conn, role_name: str) -> bool:
    """Check whether the role already exists."""
    result = conn.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s",
        (role_name,),
    )
    return result.fetchone() is not None


def main():
    # Create the test database and role if they do not exist.
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        if not database_exists(conn, TEST_DB):
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB)))

        if not role_exists(conn, TEST_USER):
            conn.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(TEST_USER),
                    sql.Literal(TEST_PASSWORD),
                )
            )

        # Ensure the test role can connect to the test database.
        conn.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(TEST_DB),
                sql.Identifier(TEST_USER),
            )
        )

    # Connect to the test database as the admin role.
    # Default privileges belong to the role that creates the objects.
    with psycopg.connect(
        TEST_ADMIN_DATABASE_URL,
        autocommit=True,
    ) as conn:
        # The test role can use the schema but cannot create objects.
        conn.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                sql.Identifier(TEST_USER)
            )
        )

        conn.execute(
            sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(
                sql.Identifier(TEST_USER)
            )
        )

        # Tables created by admin in the future get the expected
        # runtime/test privileges.
        conn.execute(
            sql.SQL(
                """
                ALTER DEFAULT PRIVILEGES
                FOR ROLE admin
                IN SCHEMA public
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON TABLES
                TO {}
                """
            ).format(sql.Identifier(TEST_USER))
        )

        # Sequences created by admin in the future allow ID generation.
        conn.execute(
            sql.SQL(
                """
                ALTER DEFAULT PRIVILEGES
                FOR ROLE admin
                IN SCHEMA public
                GRANT USAGE
                ON SEQUENCES
                TO {}
                """
            ).format(sql.Identifier(TEST_USER))
        )


if __name__ == "__main__":
    main()
