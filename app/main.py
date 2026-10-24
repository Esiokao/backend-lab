from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.database import check_database_connection
from app.routers.admin import router as admin_router
from app.routers.admin import users_router as admin_users_router
from app.routers.admin_notifications import router as admin_notifications_router
from app.routers.cart import router as cart_router
from app.routers.catalogs import router as categories_router
from app.routers.notifications import router as notifications_router
from app.routers.orders import router as order_router
from app.routers.products import router as products_router
from app.routers.stats import router as stats_router
from app.routers.users import router as users_router

app = FastAPI()


@app.middleware("http")
async def track_visitors(request, call_next):
    """匿名訪客計數：只計瀏覽器的文件導航（Accept: text/html）。

    curl／SPA 的 fetch／健康探測都是 Accept: */*，不計入，
    自動化與監控流量不會灌水訪客數。
    """
    from app.core.redis import redis_client
    from app.core.visitors import VISITOR_COOKIE, is_document_request, track_visitor

    response = await call_next(request)

    if is_document_request(request.headers.get("accept"), request.url.path):
        vid = track_visitor(redis_client, request.cookies.get(VISITOR_COOKIE))
        if VISITOR_COOKIE not in request.cookies:
            response.set_cookie(
                VISITOR_COOKIE,
                vid,
                max_age=365 * 24 * 60 * 60,
                samesite="lax",
                httponly=True,
            )
    return response


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
app.include_router(admin_router)
app.include_router(admin_users_router)
app.include_router(notifications_router)
app.include_router(admin_notifications_router)
app.include_router(categories_router)
app.include_router(cart_router)
app.include_router(products_router)
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
