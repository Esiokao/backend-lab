from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    # 建立訂單時必須指定商品。
    product_id: int = Field(gt=0)

    # 購買數量必須是正整數。
    quantity: int = Field(gt=0)
