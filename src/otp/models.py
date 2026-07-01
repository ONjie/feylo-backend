from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from src.utils.database import Base

class OTP(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=False)
    phone_number: Mapped[str] = mapped_column(String, index=True)
    otp_hash: Mapped[str] = mapped_column(String(200),)
    expiry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True),)
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )