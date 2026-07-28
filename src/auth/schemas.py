from pydantic import Field, BaseModel, field_validator
import re

class RegisterRequest(BaseModel):
    first_name: str = Field(description="Merchant's First Name")
    last_name: str = Field(description="Merchant's Last Name")
    phone_number: str = Field(description="Merchant's Phone Number")
    business_name: str=Field(description="Merchant's Business Name")

    @field_validator("phone_number")
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
    

class LoginRequest(BaseModel):
    phone_number: str = Field(description="Merchant's Phone Number")

    @field_validator("phone_number")
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


class AuthResponse(BaseModel):
    status: str = "success"
    access_token: str
    token_type: str = "bearer"
    merchant_id: str