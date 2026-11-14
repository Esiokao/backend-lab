from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.database import check_database_connection
from app.routers.admin import router as admin_router
from app.routers.admin import users_router as admin_users_router
from app.routers.admin_notifications import router as admin_notifications_router
from app.routers.cart import router as cart_router
from app.routers.catalogs import router as categories_router
from app.routers.meta import router as meta_router
from app.routers.notifications import router as notifications_router
from app.routers.orders import router as order_router
from app.routers.payments import router as payments_router
from app.routers.products import router as products_router
from app.routers.stats import router as stats_router
from app.routers.users import router as users_router
from app.routers.visitors import router as visitors_router

app = FastAPI()

# 全域 request body 上限改由 SizeLimitedAPIRouter 承擔：FastAPI >= 0.118
# 的 include_router 是惰性掛載，app.router.route_class 蓋不到 include
# 進來的路由，所以每個 router 必須自帶 route_class（見
# app/core/request_size.py 的 SizeLimitedAPIRouter）。


# 訪客追蹤（v2.6）：middleware 以「Accept: text/html 文件請求」定義訪客，
# 但 frontend 拆成靜態容器後文件請求不經過 FastAPI——指標結構性歸零。
# 改為前端 beacon：SPA mount 時主動 POST /visitors/track 報到
# （見 app/routers/visitors.py；計數邏輯仍在 app/core/visitors.py）。


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(users_router)
app.include_router(order_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(admin_users_router)
app.include_router(notifications_router)
app.include_router(admin_notifications_router)
app.include_router(categories_router)
app.include_router(cart_router)
app.include_router(products_router)
app.include_router(meta_router)
app.include_router(visitors_router)
app.include_router(stats_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: the API process can receive requests."""
    return {"status": "ok"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    """Readiness check: the API can reach PostgreSQL."""
    try:
        check_database_connection()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    return {"status": "ok"}
