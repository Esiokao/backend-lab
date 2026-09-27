import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Engine 是 SQLAlchemy 與 PostgreSQL 溝通的基礎設施。
# 它也負責管理 connection pool。
# echo=True makes SQLAlchemy print the SQL statements it sends to the database.
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# SessionLocal 是「Session 工廠」。
#
# 它本身不是一個 Session。
# 每次呼叫 SessionLocal() 才會建立一個新的 Session。
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """
    FastAPI 的 DB dependency。

    每一個 request 都建立自己的 DB Session，
    endpoint 使用完之後，離開 with 區塊時會自動關閉 Session。
    """

    # 建立一個 SQLAlchemy Session。
    # with 可以確保 Session 最後會被 cleanup。
    with SessionLocal() as session:
        # 把 Session 暫時交給 FastAPI endpoint 使用。
        #
        # yield 和 return 不同：
        # yield 會暫停這個 function，
        # endpoint 使用完之後，dependency 可以繼續執行 cleanup。
        yield session


def check_database_connection() -> None:
    """Raise SQLAlchemyError when PostgreSQL cannot accept a query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
