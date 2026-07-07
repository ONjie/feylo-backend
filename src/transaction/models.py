import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.utils.database import Base


class TxnStatus(str, Enum):
    PENDING   = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"
    EXPIRED   = "EXPIRED"
    REFUNDED  = "REFUNDED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        default=lambda: "TXN_" + uuid.uuid4().hex[:8].upper(),
    )
    merchant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("merchants.merchant_id"), index=True
    )

    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="GMD")

    status: Mapped[TxnStatus] = mapped_column(
        SAEnum(TxnStatus, name="txnstatus"),
        default=TxnStatus.PENDING,
        index=True,
    )
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # QR expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction {self.id} | {self.status} | {self.amount} {self.currency}>"
