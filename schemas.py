from pydantic import BaseModel, Field
from typing import List


class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class CreateOrder(BaseModel):
    customer_id: int = Field(..., gt=0)
    items: List[OrderItem]