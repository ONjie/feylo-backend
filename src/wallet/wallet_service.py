from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.wallet.models import Wallet, WalletLedger
from src.wallet.exceptions import WalletNotFoundError, WalletAlreadyExistError
from src.transaction.models import Transaction



async def create_wallet(merchant_id: str, session: AsyncSession) -> None:

    result = await session.execute(
        select(Wallet).where(Wallet.merchant_id == merchant_id)
    )

    existing_wallet = result.scalar_one_or_none()

    if existing_wallet:
        raise WalletAlreadyExistError(f"Wallet with merchant id: {merchant_id} already exists.")

    else:
        wallet = Wallet(merchant_id=merchant_id)

        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)


async def get_wallet(merchant_id: str, session: AsyncSession) -> Wallet:
    result = await session.execute(
        select(Wallet).where(Wallet.merchant_id == merchant_id)
    )
    existing_wallet = result.scalar_one_or_none()
    if not existing_wallet:
        raise WalletNotFoundError(f"No wallet found for merchant id: {merchant_id}")
    return existing_wallet


async def wallet_credit(txn: Transaction, session: AsyncSession) -> Wallet:
    wallet = await get_wallet(merchant_id=txn.merchant_id, session=session)
    wallet.balance = round(float(wallet.balance) + float(txn.net_amount), 2)

    ledger = WalletLedger(
        wallet_id=wallet.id,
        transaction_id=txn.id,
        entry_type="CREDIT",
        amount=txn.net_amount,
        balance_after=wallet.balance,
        description=(
            f"Payment received via {txn.payment_provider} — "
            f"{txn.currency} {txn.amount:.2f} "
            f"(fee: {txn.fee:.2f})"
        ),
    )
    session.add(ledger)
    await session.commit()
    await session.refresh(wallet)
    return wallet


async def get_wallet_ledger(
    session: AsyncSession, merchant_id: str, limit: int = 20
) -> list[WalletLedger]:
    wallet = await get_wallet(merchant_id=merchant_id, session=session)
    result = await session.execute(
        select(WalletLedger)
        .where(WalletLedger.wallet_id == wallet.id)
        .order_by(WalletLedger.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()