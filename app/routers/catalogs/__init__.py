from app.core.request_size import SizeLimitedAPIRouter

from .create_category import router as create_category_router
from .delete_category import router as delete_category_router
from .get_category import router as get_category_router
from .list_categories import router as list_categories_router
from .update_category import router as update_category_router

router = SizeLimitedAPIRouter(tags=["Categories"])
router.include_router(list_categories_router)
router.include_router(get_category_router)
router.include_router(create_category_router)
router.include_router(update_category_router)
router.include_router(delete_category_router)
