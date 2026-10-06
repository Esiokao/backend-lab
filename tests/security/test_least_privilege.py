from sqlalchemy import text

from tests.database import engine

# DB privilege policy: every application table should have only these privileges.
EXPECTED_TABLE_PRIVILEGES = {
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE",
}


def test_test_user_table_privileges():
    """Verify test_user has only the expected privileges on every public table."""
    tables_query = text(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    )

    privileges_query = text(
        """
        SELECT privilege_type
        FROM information_schema.role_table_grants
        WHERE grantee = 'test_user'
          AND table_schema = 'public'
          AND table_name = :table_name
        """
    )

    with engine.connect() as connection:
        tables = connection.execute(tables_query).scalars().all()

        for table_name in tables:
            rows = connection.execute(
                privileges_query,
                {"table_name": table_name},
            ).all()

            actual_privileges = {privilege_type for (privilege_type,) in rows}

            assert actual_privileges == EXPECTED_TABLE_PRIVILEGES, (
                f"{table_name} has unexpected privileges: {actual_privileges}"
            )
