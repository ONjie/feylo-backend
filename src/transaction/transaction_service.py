from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.transaction.models import Transaction, TxnStatus
from src.payment.schemas import WebhookPayload
from src.utils.config import settings
from src.transaction.exceptions import TransactionNotFoundError
from sqlalchemy.orm import selectinload


async def create_pending_transaction(
    merchant_id: str, amount: float, session: AsyncSession
) -> Transaction:
    fee = round(amount * settings.PLATFORM_FEE_PCT, 2)
    net_amount = round(amount - fee, 2)

    txn = Transaction(
        merchant_id=merchant_id,
        amount=amount,
        fee=fee,
        net_amount=net_amount,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.QR_EXPIRY_MINUTES),
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    return txn


async def get_transaction_by_id(transaction_id: str, session: AsyncSession) -> Transaction:

    result = await session.execute(
    select(Transaction)
    .options(selectinload(Transaction.merchant))
    .where(Transaction.id == transaction_id)
    )

    existing_transaction = result.scalar_one_or_none()

    if not existing_transaction:
        raise TransactionNotFoundError(f"Transaction {transaction_id} not found")

    return existing_transaction


async def complete_transaction(
    txn: Transaction, payload: WebhookPayload, session: AsyncSession
) -> Transaction:
    now = datetime.now(timezone.utc)
    txn.status = TxnStatus.COMPLETED
    txn.payment_provider = payload.payment_provider
    txn.external_ref = payload.external_reference
    txn.customer_phone_number = payload.customer_phone_number
    txn.customer_full_name = payload.customer_full_name
    txn.completed_at = now
    await session.commit()
    await session.refresh(txn)
    return txn


async def failed_transaction(txn: Transaction, session: AsyncSession) -> Transaction:
    txn.status = TxnStatus.FAILED
    await session.commit()
    return txn


async def get_transactions_list(
    session: AsyncSession,
    merchant_id: str,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Transaction], int]:
    offset = (page - 1) * per_page

    count_result = await session.execute(
        select(func.count()).where(Transaction.merchant_id == merchant_id)
    )
    total = count_result.scalar_one()

    if total == 0:
        raise TransactionNotFoundError(f"No transactions found for merchant {merchant_id}")

    result = await session.execute(
        select(Transaction)
        .where(Transaction.merchant_id == merchant_id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )

    return result.scalars().all(), total


async def expired_transaction(txn: Transaction, session: AsyncSession) -> Transaction:
    txn.status = TxnStatus.EXPIRED
    await session.commit()
    return txn