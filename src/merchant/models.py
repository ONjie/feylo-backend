from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime
import uuid
from datetime import datetime, timezone
from src.utils.database import Base

class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(
        String(16), primary_key=True,
        default=lambda: "MERCH_" + str(uuid.uuid4().hex[:10]).replace("-", "").upper(),
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_number: Mapped[str] = mapped_column(String, index=True, nullable=False)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    pin_code: Mapped[str] = mapped_column(String(4), nullable=True)
    is_verified: Mapped[bool] =  mapped_column(Boolean, default=False)
    is_active: Mapped[bool] =  mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="merchant", lazy="select"
    )
    wallet: Mapped["Wallet"] = relationship(
        back_populates="merchant", uselist=False, lazy="select"
    ) 