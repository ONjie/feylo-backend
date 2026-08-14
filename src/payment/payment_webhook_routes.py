import logging, sys
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.database import get_db_session
from src.payment.schemas import WebhookPayload, WebhookResponse
from src.transaction.transaction_service import (
    get_transaction_by_id, 
    complete_transaction, 
    failed_transaction, 
    expired_transaction
)
from src.transaction.models import TxnStatus
from src.auth.security import verify_signature
from src.wallet.wallet_service import wallet_credit
from src.websocket.websocket_manager import manager
from datetime import datetime, timezone, timedelta


router = APIRouter(prefix="/payments", tags=["webhook"])

logging.basicConfig(
    level=logging.INFO,                                
    format="%(asctime)s [%(levelname)s] %(message)s",  
    handlers=[logging.StreamHandler(sys.stdout)]  
)
logger = logging.getLogger(__name__)



@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Receives payment confirmation from Wave / AfriMoney / QMoney.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not verify_signature(raw_body, signature):
        logger.warning("Webhook rejected — invalid HMAC signature")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    payload = WebhookPayload.model_validate_json(raw_body)
    logger.info(f"Webhook received: {payload.transaction_id} via {payload.payment_provider}")

    txn = await get_transaction_by_id(transaction_id=payload.transaction_id, session=session)

    if txn.status != TxnStatus.PENDING:
        logger.info(f"Duplicate webhook ignored for {payload.transaction_id}")
        return WebhookResponse()
    

    current_time = datetime.now(timezone.utc)
    
    if txn.expires_at and current_time > txn.expires_at:
        logger.warning(f"Webhook rejected — Transaction {txn.id} expired at {txn.expires_at}")
        
        await expired_transaction(txn=txn, session=session)
        
        try:
            await manager.broadcast(txn.merchant_id, {
                "event": "PAYMENT_EXPIRED",
                "txn_id": txn.id,
                "amount": float(txn.amount),
                "currency": txn.currency
            })
        except Exception as redis_err:
            logger.error(f"WebSocket notification failed for expired txn {txn.id}: {redis_err}")
            
        return WebhookResponse()

    if payload.status == "SUCCESS":
        txn = await complete_transaction(txn=txn, payload=payload, session=session)
        await wallet_credit(txn=txn, session=session)
        try:

            await manager.broadcast(txn.merchant_id, {
                "event": "PAYMENT_RECEIVED",
                "txn_id": txn.id,
                "amount": float(txn.amount),
                "net_amount": float(txn.net_amount),
                "fee": float(txn.fee),
                "currency": txn.currency,
                "provider": txn.payment_provider,
                "customer_phone_number": txn.customer_phone_number,
                "customer_full_name": txn.customer_full_name,
            })
            logger.info(f"Payment completed: {txn.id} | {txn.amount} GMD via {txn.payment_provider}")

        except Exception as redis_err:
            logger.error(f"WebSocket notification failed for expired txn {txn.id}: {redis_err}")
           
    else:
        await failed_transaction(txn=txn, session=session)
        logger.warning(f"Payment failed: {txn.id}")

    return WebhookResponse()
