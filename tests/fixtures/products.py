from decimal import Decimal

import pytest

from app.models import Product


@pytest.fixture
def create_test_product(test_db):
    def _create_product(
        *,
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
        is_active=True,
    ):
        product = Product(
            name=name,
            price=price,
            stock=stock,
            is_active=is_active,
        )
        test_db.add(product)
        test_db.flush()

        # flush 後可以取得資料庫產生的 product.id。
        return product

    return _create_product
