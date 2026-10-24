from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Catalog
from app.schemas.Catalog import CatalogResponse

router = APIRouter(prefix="/catalogs")


@router.get("/{catalog_id}", response_model=CatalogResponse)
def get_catalog(catalog_id: int, db: Session = Depends(get_db)):
    catalog = db.scalar(select(Catalog).where(Catalog.id == catalog_id))
    if catalog is None:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog
