# tests/migrations/test_schema_drift.py
# models ↔ migrations 漂移偵測。
#
# 為什麼需要：CI 只驗證「migrations 跑得動、測試會過」。如果改了
# app/models.py 卻忘了寫 migration（或反向），測試資料庫與 model 會
# 靜靜分岔——部署到生產環境升級時才爆炸。
#
# 做法：在獨立的 scratch database 上執行 `alembic upgrade head`
# （完整 migration 鏈，不碰共用的 test db），再用 alembic autogenerate
# 的比對器 compare_metadata 拿 model metadata 對照實際 schema。
# diff 非空 = 漂移 = 測試紅，訊息直接列出缺什麼。

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.models import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_DB = "backend_lab_drift_test"


def _url(database: str):
    """由 TEST_ADMIN_DATABASE_URL 衍生連線 URL（統一 psycopg driver）。"""
    admin_url = os.environ.get("TEST_ADMIN_DATABASE_URL")
    if not admin_url:
        pytest.skip("TEST_ADMIN_DATABASE_URL is not set")

    url = make_url(admin_url).set(database=database)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


@pytest.fixture
def migrated_engine():
    """建 scratch db → 跑完整 migration 鏈 → yield engine → 清掉。"""
    admin_engine = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{SCRATCH_DB}"'))

    # env.py 在無 -x db=test 時讀 MIGRATION_DATABASE_URL；
    # python-dotenv 預設不覆蓋已存在的環境變數，所以這個覆寫有效。
    # 注意：str(url) 會把密碼遮成 ***（SQLAlchemy 的安全渲染），
    # 餵給 env.py 必須用 render_as_string(hide_password=False)。
    scratch_url = _url(SCRATCH_DB)
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = scratch_url.render_as_string(
        hide_password=False
    )

    try:
        alembic_config = Config(str(REPO_ROOT / "alembic.ini"))
        command.upgrade(alembic_config, "head")
    finally:
        if previous is None:
            os.environ.pop("MIGRATION_DATABASE_URL", None)
        else:
            os.environ["MIGRATION_DATABASE_URL"] = previous

    engine = create_engine(scratch_url)  # URL 物件可直接餵 create_engine
    yield engine

    engine.dispose()
    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)'))
    admin_engine.dispose()


def test_models_match_migrated_schema(migrated_engine):
    """alembic upgrade head 之後的 schema 必須與 app/models.py 完全一致。"""
    with migrated_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)

    assert diff == [], (
        "app/models.py 與 alembic migrations 漂移了——"
        "改了 model 記得產 migration（alembic revision --autogenerate）：\n"
        f"{diff}"
    )
