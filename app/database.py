from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


# PostgreSQL 的連線資訊
#
# 格式：
# postgresql+psycopg://使用者:密碼@主機:Port/Database
DATABASE_URL = "postgresql+psycopg://admin:adminpass@localhost:5432/backend_lab"


# Engine 是 SQLAlchemy 與 PostgreSQL 溝通的基礎設施。
# 它也負責管理 connection pool。
# echo=True makes SQLAlchemy print the SQL statements it sends to the database.
engine = create_engine(
    DATABASE_URL,
    echo=True,
)


# Base.metadata 裡面收集了所有 SQLAlchemy Model 的 table 定義。
#
# create_all()：
# - table 不存在 → 建立 table
# - table 已存在 → 不會重新建立
#
# 注意：它不是 migration tool，不會自動修改既有 table。
Base.metadata.create_all(engine)


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