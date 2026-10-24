from fastapi import APIRouter

from .create_catalog import router as create_catalog_router
from .delete_catalog import router as delete_catalog_router
from .get_catalog import router as get_catalog_router
from .list_catalogs import router as list_catalogs_router
from .update_catalog import router as update_catalog_router

router = APIRouter(tags=["Catalogs"])
router.include_router(list_catalogs_router)
router.include_router(get_catalog_router)
router.include_router(create_catalog_router)
router.include_router(update_catalog_router)
router.include_router(delete_catalog_router)
