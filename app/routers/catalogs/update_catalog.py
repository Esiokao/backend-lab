from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Catalog, User
from app.schemas.Catalog import CatalogPatch, CatalogResponse

router = APIRouter(prefix="/catalogs")


@router.patch("/{catalog_id}", response_model=CatalogResponse)
def update_catalog(
    catalog_id: int,
    payload: CatalogPatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    catalog = db.get(Catalog, catalog_id)
    if catalog is None:
        raise HTTPException(status_code=404, detail="Catalog not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(catalog, field, value)

    db.commit()
    db.refresh(catalog)
    return catalog
