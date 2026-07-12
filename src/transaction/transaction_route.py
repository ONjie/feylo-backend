from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.database import get_db_session
from src.merchant.schemas import MerchantRead
from src.auth.security import get_current_merchant
from src.transaction.schemas import TransactionRead, TransactionListResponse
from src.transaction.transaction_service import (
    get_transaction_by_id, 
    get_transactions_list
    )
from src.transaction.exceptions import TransactionNotFoundError


router = APIRouter(prefix="/transactions", tags=["transactions"])



@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction_id_endpoint(
    transaction_id: str,
    merchant: MerchantRead = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        transaction = await get_transaction_by_id(transaction_id=transaction_id, session=session)

        if transaction.merchant_id != merchant.merchant_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your transaction")
        return TransactionRead.model_validate(transaction)
    except TransactionNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("", response_model=TransactionListResponse)
async def get_transactions_list_endpoint(
    page: int = 1,
    per_page: int = 20,
    merchant: MerchantRead = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
):
    
    try:
        transactions, total = await get_transactions_list(
            session=session, 
            merchant_id=merchant.merchant_id, 
            page=page, 
            per_page=per_page
        )
        return TransactionListResponse(
            transactions=[TransactionRead.model_validate(t) for t in transactions], 
            total=total, 
            page=page, 
            per_page=per_page
            )
   

    except TransactionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)