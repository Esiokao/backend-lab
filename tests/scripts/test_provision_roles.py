# tests/scripts/test_provision_roles.py
# provision_roles 的所有權轉移：表附屬序列（SERIAL）不能單獨 ALTER OWNER
# （PostgreSQL 禁止），必須排除——它們隨所屬表自動轉移。
# 回歸背景：notification_outbox_id_seq 曾讓 AWS 部署的 db-roles 隨機炸
# （FeatureNotSupported，取決於關系列舢順序）。

import importlib.util
from pathlib import Path

import psycopg
import pytest

# scripts/ 不是套件（獨立腳本目錄）——按路徑載入模組。
_spec = importlib.util.spec_from_file_location(
    "provision_roles",
    Path(__file__).resolve().parents[2] / "scripts" / "provision_roles.py",
)
provision_roles_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(provision_roles_mod)
provision_roles = provision_roles_mod.provision_roles


@pytest.fixture
def admin_url(monkeypatch) -> str:
    """把 provision_roles 需要的 env 指到測試 DB（admin 帳號）。"""
    from tests.database import TEST_DATABASE_URL

    # TEST_DATABASE_URL 用 app 帳號；admin 連線換 admin 帳號、同 DB。
    # URL 是 SQLAlchemy 格式（postgresql+psycopg://），raw psycopg 不認，剝掉方言。
    plain = TEST_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    admin = plain.replace("test_user:testuserpass", "admin:adminpass")
    monkeypatch.setenv("MIGRATION_ADMIN_DATABASE_URL", admin)
    monkeypatch.setenv("APP_DB_PASSWORD", "appuserpass")
    monkeypatch.setenv("MIGRATION_DB_PASSWORD", "migrationuserpass")
    return admin


def test_ownership_transfer_skips_table_owned_sequences(admin_url, test_db):
    # 佈景：SERIAL 表（附屬序列）＋ 自由序列（無歸屬）。
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS dummy_serial (id serial, note text)")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS dummy_free_seq")

    provision_roles()  # 修正前：這裡會炸 FeatureNotSupported

    with psycopg.connect(admin_url, autocommit=True) as conn:
        owners = dict(
            conn.execute(
                "SELECT c.relname, r.rolname FROM pg_class c "
                "JOIN pg_roles r ON r.oid = c.relowner "
                "WHERE c.relname IN ('dummy_serial', 'dummy_serial_id_seq', 'dummy_free_seq')"
            ).fetchall()
        )

    assert owners["dummy_serial"] == "migration_user"  # 表本身轉移
    assert owners["dummy_serial_id_seq"] == "migration_user"  # 附屬序列隨表自動轉移
    assert owners["dummy_free_seq"] == "migration_user"  # 自由序列直接轉移

    # 清理：轉回 admin 再 drop（owner 是 migration_user 時 drop 需要權限）。
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute("REASSIGN OWNED BY migration_user TO admin")
        conn.execute("DROP TABLE IF EXISTS dummy_serial")
        conn.execute("DROP SEQUENCE IF EXISTS dummy_free_seq")
