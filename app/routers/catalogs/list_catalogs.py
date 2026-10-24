from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Catalog
from app.schemas.Catalog import CatalogResponse

router = APIRouter(prefix="/catalogs")


@router.get("/", response_model=list[CatalogResponse])
def list_catalogs(db: Session = Depends(get_db)):
    return db.scalars(select(Catalog).order_by(Catalog.id)).all()
