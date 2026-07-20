from pydantic import BaseModel

class CheckoutPayRequest(BaseModel):
    payment_provider: str            
    customer_phone_number: str