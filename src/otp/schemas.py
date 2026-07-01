from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re

class OTPCreate(BaseModel):
    phone_number: str = Field(description="Merchant's phone number")
    raw_otp: int = Field(description="The Raw Generated OTP")
    hashed_otp: str = Field(description="The Hashed Generated OTP")
    expiry_time: datetime = Field(description="OTP Expiration Time")


class OTPRead(OTPCreate):
    id: int
    otp_attempts: int
    created_at: datetime
    model_config = {"from_attributes": True}


class OTPSentResponse(BaseModel):
    message: str
    expires_in_seconds: int = 600

class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(description="Merchant's phone number")
    submitted_otp: str = Field(description="The OTP submitted by the merchant")

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

    @field_validator("submitted_otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v
    

class ResendOTPRequest(BaseModel):
    phone_number: str = Field(description="Merchant's phone number")

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