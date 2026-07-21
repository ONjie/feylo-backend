from pydantic import BaseModel, field_validator
import re

class CheckoutPayRequest(BaseModel):
    payment_provider: str            
    customer_phone_number: str

    @field_validator("customer_phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Normalizes and validates Gambian phone numbers."""
        cleaned = v.replace(" ", "").replace("-", "")
        
        pattern = re.compile(r"^(\+?220)?([23579]\d{6})$")
        match = pattern.match(cleaned)
        
        if not match:
            raise ValueError("Invalid Gambian phone number format. Must be a valid 7-digit local number or include the 220 prefix.")
        
        local_part = match.group(2)
        return f"+220{local_part}"