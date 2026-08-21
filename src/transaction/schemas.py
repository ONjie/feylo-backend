from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionRead(BaseModel):
    id: str
    amount: float
    fee: float
    net_amount: float
    currency: str
    status: str
    payment_provider: Optional[str]
    customer_phone_number: Optional[str]
    customer_full_name: Optional[str]
    external_ref: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    business_name: Optional[str] = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionRead]
    total: int
    page: int
    per_page: int