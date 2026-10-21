# app/routers/notifications/__init__.py

from fastapi import APIRouter

from .list_notifications import router as list_router
from .mark_all_notification_read import router as mark_all_read_router
from .mark_notification_read import router as mark_read_router
from .unread_count import router as unread_count_router

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

router.include_router(list_router)
router.include_router(mark_read_router)
router.include_router(unread_count_router)
router.include_router(mark_all_read_router)
