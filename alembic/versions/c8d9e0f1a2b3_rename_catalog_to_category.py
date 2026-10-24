"""rename catalogs to categories"""

from typing import Sequence, Union

from alembic import op


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c4d5e6f708"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_products_catalog_id_catalogs", "products", type_="foreignkey"
    )
    op.alter_column("products", "catalog_id", new_column_name="category_id")
    op.rename_table("catalogs", "categories")
    op.create_foreign_key(
        "fk_products_category_id_categories",
        "products",
        "categories",
        ["category_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_products_category_id_categories", "products", type_="foreignkey"
    )
    op.rename_table("categories", "catalogs")
    op.alter_column("products", "category_id", new_column_name="catalog_id")
    op.create_foreign_key(
        "fk_products_catalog_id_catalogs",
        "products",
        "catalogs",
        ["catalog_id"],
        ["id"],
    )
