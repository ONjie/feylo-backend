from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.payment.schemas import QRRequest, QRResponse
from src.payment.payment_service import generate_qr_code
from src.merchant.schemas import MerchantRead
from src.transaction.transaction_service import create_pending_transaction
from src.utils.database import get_db_session
from src.auth.security import get_current_merchant

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

    return QRResponse(
        txn_id=transaction.id,
        qr_url=f"{merchant.merchant_id}/{transaction.id}",
        qr_image_b64=qr_b64,
        amount=transaction.amount,
        currency=transaction.currency,
        expires_at=transaction.expires_at,
    )
