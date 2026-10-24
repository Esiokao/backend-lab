from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Catalog, Product, User

router = APIRouter(prefix="/catalogs")


@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog(
    catalog_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    catalog = db.get(Catalog, catalog_id)
    if catalog is None:
        raise HTTPException(status_code=404, detail="Catalog not found")

    # Products may exist without a catalog, so unlink them before deleting it.
    db.execute(
        update(Product).where(Product.catalog_id == catalog_id).values(catalog_id=None)
    )
    db.delete(catalog)
    db.commit()
