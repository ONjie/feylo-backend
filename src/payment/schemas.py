from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class QRRequest(BaseModel):
    amount: float = Field(gt=0, description="Payment amount in GMD")


class QRResponse(BaseModel):
    txn_id: str
    qr_url: str
    qr_image_b64: str
    amount: float
    currency: str
    business_name:str
    expires_at: datetime


class WebhookPayload(BaseModel):
    transaction_id: str
    payment_provider: str
    amount: float
    status: str              
    external_reference: str
    customer_phone_number: Optional[str] = None


class WebhookResponse(BaseModel):
    received: bool = True    

