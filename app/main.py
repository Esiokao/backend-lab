from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.database import check_database_connection
from app.routers.admin import router as admin_router
from app.routers.admin import users_router as admin_users_router
from app.routers.admin_notifications import router as admin_notifications_router
from app.routers.notifications import router as notifications_router
from app.routers.orders import router as order_router
from app.routers.users import router as users_router

app = FastAPI()


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
