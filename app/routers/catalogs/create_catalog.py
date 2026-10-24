from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Catalog, User
from app.schemas.Catalog import CatalogCreate, CatalogResponse

router = APIRouter(prefix="/catalogs")


@router.post("/", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
def create_catalog(
    payload: CatalogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    catalog = Catalog(name=payload.name, description=payload.description)
    db.add(catalog)
    db.commit()
    db.refresh(catalog)
    return catalog
