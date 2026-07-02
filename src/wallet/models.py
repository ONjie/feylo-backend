from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.utils.database import Base
import uuid


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    merchant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("merchants.merchant_id"), unique=True, index=True
    )
    balance: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="GMD")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="wallet")
    ledger: Mapped[list["WalletLedger"]] = relationship(
        back_populates="wallet", order_by="WalletLedger.created_at.desc()"
    )


class WalletLedger(Base):
    __tablename__ = "wallet_ledger"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id"), index=True
    )
    transaction_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(20)) 
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[float] = mapped_column(Numeric(14, 2))
    description: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="ledger")


