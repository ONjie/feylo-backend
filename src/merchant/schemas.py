from pydantic import Field, BaseModel, field_validator
from typing import List
import re

class MerchantCreate(BaseModel):
    first_name: str = Field(description="Merchant's First Name", min_length=3, max_length=50)
    last_name: str = Field(description="Merchant's Last Name", min_length=3, max_length=50)
    phone_number: str = Field(description="Merchant's Phone Number")
    business_name: str=Field(description="Merchant's Business Name", min_length=5, max_length=200)
    

class MerchantRead(BaseModel):
    merchant_id: str
    first_name: str
    last_name: str
    phone_number: str
    is_active: bool
    is_verified: bool
    business_name: str
    #transactions: List[TransactionRead] =[]
    #wallet: WalletRead = None

    model_config = {"from_attributes": True}