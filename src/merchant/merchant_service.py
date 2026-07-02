from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from src.merchant.models import Merchant
from src.merchant.schemas import MerchantCreate, MerchantRead
from src.merchant.exceptions import (
    MerchantNotFoundError, 
    MerchantAlreadyExistError, 
    InvalidMerchantLookupError
    )
from typing import Optional


async def create_merchant(merchant: MerchantCreate, session:AsyncSession) -> MerchantRead:

    result = await session.execute(select(Merchant).where(Merchant.phone_number == merchant.phone_number))

    if result.scalar_one_or_none():
        raise MerchantAlreadyExistError(
            f"Merchant account with phone number {merchant.phone_number} already exists."
            )

    db_merchant = Merchant(
        first_name = merchant.first_name,
        last_name=merchant.last_name,
        business_name=merchant.business_name,
        phone_number=merchant.phone_number
    )

    session.add(db_merchant)
    await session.commit()
    
    return await get_merchant(session=session, merchant_id=db_merchant.merchant_id)
    
    

async def get_merchant(
        session:AsyncSession,
        merchant_id: Optional[str] = None, 
        phone_number: Optional[str] = None
        ) -> MerchantRead:
    if not merchant_id and not phone_number:
        raise InvalidMerchantLookupError("Either merchant_id or phone_number must be provided.")
    
    query = select(Merchant).options(
        selectinload(Merchant.transactions),
        selectinload(Merchant.wallet)
    )

    if merchant_id:
        query = query.where(Merchant.merchant_id == merchant_id)
    if phone_number: 
        query = query.where(Merchant.phone_number == phone_number)
    
    result = await session.execute(
       query
    )

    existing_merchant = result.scalar_one_or_none()

    if not existing_merchant:
        identifier = merchant_id or phone_number
        raise MerchantNotFoundError(f"Merchant {identifier} not found.")
    return MerchantRead.model_validate(existing_merchant)


async def deactivate_merchant_account(merchant_id: str, session:AsyncSession) ->MerchantRead:
    await session.execute(
        update(Merchant)
        .where(Merchant.merchant_id == merchant_id)
        .values(is_active=False)
    )

    await session.commit()

    updated_merchant = await get_merchant(merchant_id=merchant_id, session=session)
    return updated_merchant


async def update_merchant_is_verified_status(merchant_id: str, session:AsyncSession) ->MerchantRead:
    await session.execute(
        update(Merchant)
        .where(Merchant.merchant_id == merchant_id)
        .values(is_verified=True)
    )
    
    await session.commit()
    
    updated_merchant = await get_merchant(merchant_id=merchant_id, session=session)
    return updated_merchant


