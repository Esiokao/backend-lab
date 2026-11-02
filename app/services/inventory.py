# app/services/inventory.py
# 庫存歸還的單一真相來源：所有「取消」路徑（owner cancel、過期 worker、admin）
# 都必須經過這裡——三處各寫一份就會出現「admin 取消不還庫存」的不一致。

from sqlalchemy import select, update

from app.models import OrderItem, Product


def restore_order_stock(session, order_id: int) -> dict[int, int]:
    """歸還一筆訂單建單時佔用的庫存（依 product_id 排序，死鎖免疫）。

    呼叫端責任：與訂單狀態變更同一交易（呼叫端 commit）；
    只在「轉移進 cancelled」時呼叫一次——重複呼叫會重複歸還。
    回傳 {product_id: 歸還數量}。
    """
    items = (
        session.execute(select(OrderItem).where(OrderItem.order_id == order_id))
        .scalars()
        .all()
    )

    quantities = {item.product_id: item.quantity for item in items}
    for product_id in sorted(quantities):
        session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(stock=Product.stock + quantities[product_id])
        )

    return quantities
