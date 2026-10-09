"""Provision PostgreSQL roles and least-privilege permissions."""

import os
import sys

import psycopg
from psycopg import sql

DATABASE_NAME = "backend_lab"
APP_ROLE = "app_user"
MIGRATION_ROLE = "migration_user"


def required_env(name: str) -> str:
    """Read a required environment variable without exposing its value."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def create_or_update_role(
    cursor: psycopg.Cursor,
    role_name: str,
    password: str,
) -> None:
    """Create a login role or update its password and privilege flags."""
    cursor.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s",
        (role_name,),
    )
    role_exists = cursor.fetchone() is not None

    if role_exists:
        cursor.execute(
            sql.SQL(
                "ALTER ROLE {} WITH LOGIN PASSWORD {} "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
            ).format(
                sql.Identifier(role_name),
                sql.Literal(password),
            )
        )
    else:
        cursor.execute(
            sql.SQL(
                "CREATE ROLE {} WITH LOGIN PASSWORD {} "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
            ).format(
                sql.Identifier(role_name),
                sql.Literal(password),
            )
        )


def provision_roles() -> None:
    """Create application roles and grant required database permissions."""
    admin_database_url = required_env("MIGRATION_ADMIN_DATABASE_URL")
    app_password = required_env("APP_DB_PASSWORD")
    migration_password = required_env("MIGRATION_DB_PASSWORD")

    # This connection must use a database administrator account.
    with (
        psycopg.connect(admin_database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        # Create or update both roles without administrative privileges.
        create_or_update_role(cursor, APP_ROLE, app_password)
        create_or_update_role(cursor, MIGRATION_ROLE, migration_password)

        # Permit both roles to connect to the application database.
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}, {}").format(
                sql.Identifier(DATABASE_NAME),
                sql.Identifier(APP_ROLE),
                sql.Identifier(MIGRATION_ROLE),
            )
        )

        # Keep the runtime role from inheriting the public schema's default
        # CREATE privilege.
        cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

        # Existing objects may have been created by admin before the
        # dedicated migration role existed. Transfer ownership so future
        # Alembic revisions can alter them.
        cursor.execute(
            """
                SELECT c.relkind, c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p', 'S')
                """
        )
        for relkind, relation_name in cursor.fetchall():
            statement = (
                "ALTER SEQUENCE {} OWNER TO {}"
                if relkind == "S"
                else "ALTER TABLE {} OWNER TO {}"
            )
            cursor.execute(
                sql.SQL(statement).format(
                    sql.Identifier("public", relation_name),
                    sql.Identifier(MIGRATION_ROLE),
                )
            )

        # Only the migration role may create objects in the public schema.
        cursor.execute(
            sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(
                sql.Identifier(MIGRATION_ROLE)
            )
        )
        cursor.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                sql.Identifier(APP_ROLE)
            )
        )

        # Grant runtime access to existing tables and sequences.
        cursor.execute(
            sql.SQL(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                "ON ALL TABLES IN SCHEMA public TO {}"
            ).format(sql.Identifier(APP_ROLE))
        )
        cursor.execute(
            sql.SQL(
                "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}"
            ).format(sql.Identifier(APP_ROLE))
        )

        # Set default runtime permissions for future migration-owned tables.
        cursor.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
            ).format(
                sql.Identifier(MIGRATION_ROLE),
                sql.Identifier(APP_ROLE),
            )
        )
        cursor.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO {}"
            ).format(
                sql.Identifier(MIGRATION_ROLE),
                sql.Identifier(APP_ROLE),
            )
        )

    print("Database role provisioning completed.")


if __name__ == "__main__":
    try:
        provision_roles()
    except (psycopg.Error, RuntimeError) as exc:
        # Avoid logging connection strings, passwords, or SQL details.
        print(
            f"Database role provisioning failed: {type(exc).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
