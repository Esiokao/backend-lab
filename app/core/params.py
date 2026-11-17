"""路徑與查詢參數的共用型別——把整數參數綁在 PostgreSQL 的儲存範圍內。

裸 int 沒有上界：Python 的 int 無限精度，fuzzer（Schemathesis）會生成
2**63 這類邊界值，一路傳到 PostgreSQL 才因 INTEGER/BIGINT 溢出炸成 500
（psycopg.errors.NumericValueOutOfRange，2026-11-17 fuzzing 實抓）。

在 FastAPI 參數層擋下（422），範圍同時寫進 OpenAPI schema，
讓 schema 驅動工具生成「範圍內」的測試值——測真實行為而非崩潰。
"""

from typing import Annotated

from fastapi import Path, Query

# PostgreSQL INTEGER 上限：2**31 - 1（模型主鍵一律為 INTEGER 欄位）
PG_INTEGER_MAX = 2_147_483_647

# 路徑參數：/{user_id}、/{product_id}、/{order_id}……
DbId = Annotated[int, Path(gt=0, le=PG_INTEGER_MAX)]

# 查詢參數：分頁頁碼（default=1，未帶參數時可省略）
Page = Annotated[int, Query(ge=1, le=PG_INTEGER_MAX)]

# 查詢參數：可省略的 id 過濾（如 /products?category_id=...）
CategoryIdParam = Annotated[int | None, Query(gt=0, le=PG_INTEGER_MAX)]
