from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.database import get_db_session
from src.checkout.schemas import CheckoutPayRequest
from src.transaction.transaction_service import get_transaction_by_id
from src.payment.payment_simulator import execute_simulated_webhook
from src.transaction.models import TxnStatus
from src.transaction.exceptions import TransactionNotFoundError
from src.transaction.schemas import TransactionRead


router = APIRouter(prefix="/checkout",tags=["checkout"])



@router.get("/{transaction_id}", response_model=TransactionRead)
async def checkout_endpoint(
    transaction_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> TransactionRead:
    try:
        transaction = await get_transaction_by_id(transaction_id=transaction_id, session=session)

        if transaction.status == TxnStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This payment has already been completed.")
        if transaction.status in (TxnStatus.FAILED, TxnStatus.EXPIRED):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This payment link has expired.")

        return TransactionRead.model_validate(transaction)
    
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)



@router.post("/{transaction_id}/pay")
async def initiate_payment_endpoint(
    transaction_id: str,
    body: CheckoutPayRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
):
    try:
    
        txn = await get_transaction_by_id(transaction_id=transaction_id, session=session)

        if txn.status != TxnStatus.PENDING:
            raise HTTPException(status.HTTP_409_CONFLICT, "Transaction is no longer pending")

        valid_payment_providers = {"wave", "afrimoney", "qmoney", "aps"}
        if body.payment_provider.lower() not in valid_payment_providers:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown provider")

        background_tasks.add_task(
            execute_simulated_webhook,
            transaction_id,
            body.payment_provider.lower(),
            float(txn.amount),
            body.customer_phone_number,
            body.customer_full_name,
        )
        return {"status": "processing", "message": "Check your phone for PIN prompt"}
    
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
