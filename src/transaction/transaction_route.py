from fastapi import APIRouter, Depends
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



@router.get("/{txn_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: str,
    merchant: MerchantRead = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        transaction = await get_transaction_by_id(transaction_id=transaction_id, session=session)

        if transaction.merchant_id != merchant.merchant_id:
            from fastapi import HTTPException, status
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your transaction")
        return transaction
    except TransactionNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page: int = 1,
    per_page: int = 20,
    merchant: MerchantRead = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
):
    
    transactions, total = await get_transactions_list(
        session=session, 
        merchant_id=merchant.merchant_id, 
        page=page, 
        per_page=per_page
    )
    return TransactionListResponse(
        transactions=transactions, 
        total=total, 
        page=page, 
        per_page=per_page)
