from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.payment.schemas import QRRequest, QRResponse
from src.payment.payment_service import generate_qr_code
from src.merchant.schemas import MerchantRead
from src.transaction.transaction_service import create_pending_transaction, get_transaction_by_id
from src.utils.database import get_db_session
from src.auth.security import get_current_merchant
from src.utils.config import settings
from src.transaction.exceptions import TransactionNotFoundError

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/generate-qr-code", 
    response_model=QRResponse, 
    status_code=status.HTTP_201_CREATED)
async def generate_qr_code_endpoint(
    payload: QRRequest,
    merchant: MerchantRead = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
):
    transaction = await create_pending_transaction(
        merchant_id=merchant.merchant_id, 
        amount=payload.amount,
        session=session)
    
    qr_b64 = generate_qr_code(transaction_id=transaction.id)

    checkout_url = f"{settings.BASE_URL}/api/v1/checkout/{transaction.id}"

    return QRResponse(
        txn_id=transaction.id,
        qr_url=checkout_url,
        qr_image_b64=qr_b64,
        business_name=merchant.business_name,
        amount=transaction.amount,
        currency=transaction.currency,
        expires_at=transaction.expires_at,
    )

