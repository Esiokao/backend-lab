# tests/fixtures/database.py

import pytest
from sqlalchemy.orm import Session

from tests.database import engine


@pytest.fixture
def test_db():
    # 建立測試用的 database connection。
    connection = engine.connect()

    # 開啟 transaction。
    transaction = connection.begin()

    print(">>> OUTER TRANSACTION BEGIN")

    # Session 使用這條 connection。
    session = Session(bind=connection)

    yield session

    print(">>> OUTER TRANSACTION ROLLBACK")

    # 測試結束後回滾資料。
    transaction.rollback()

    # 關閉 Session。
    session.close()

    # 關閉 connection。
    connection.close()
