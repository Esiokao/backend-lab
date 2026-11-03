from app.core.request_size import SizeLimitedAPIRouter

from .archive_product import router as archive_product_router
from .create_product import router as create_product_router
from .delete_product import router as delete_product_router
from .follow_product import router as follow_product_router
from .get_product import router as get_product_router
from .list_archived_products import (
    router as list_archived_products_router,
)
from .list_products import router as list_products_router
from .restore_product import router as restore_product_router
from .update_product import router as update_product_router

router = SizeLimitedAPIRouter(tags=["Products"])

router.include_router(list_archived_products_router)
router.include_router(archive_product_router)
router.include_router(restore_product_router)
router.include_router(list_products_router)
router.include_router(get_product_router)
router.include_router(create_product_router)
router.include_router(update_product_router)
router.include_router(follow_product_router)
router.include_router(delete_product_router)
