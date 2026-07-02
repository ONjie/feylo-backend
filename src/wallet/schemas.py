from pydantic import BaseModel
from datetime import datetime


class WalletRead(BaseModel):
    id: str
    balance: float
    currency: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class LedgerEntry(BaseModel):
    id: str
    entry_type: str
    amount: float
    balance_after: float
    description: str
    transaction_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletWithLedger(BaseModel):
    wallet: WalletRead
    recent_entries: list[LedgerEntry]
