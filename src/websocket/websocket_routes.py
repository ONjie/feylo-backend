from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.database import get_db_session
from src.merchant.merchant_service import get_merchant
from src.websocket.websocket_manager import manager
from src.auth.security import decode_access_token
from src.auth.exceptions import InvalidTokenError
from src.merchant.exceptions import MerchantNotFoundError
import logging
import sys

logging.basicConfig(
    level=logging.INFO,                                
    format="%(asctime)s [%(levelname)s] %(message)s",  
    handlers=[logging.StreamHandler(sys.stdout)]  
)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/merchant/{merchant_id}")
async def merchant_websocket_endpoint(
    ws: WebSocket,
    merchant_id: str,
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    try:  
        token_merchant_id = decode_access_token(token=token)
        if token_merchant_id != merchant_id:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Wrong merchant id")
            return
            
        merchant = await get_merchant(merchant_id=merchant_id, session=session)
        if not merchant.is_active or not merchant.is_verified:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Merchant is not verified or active")
            return

    except (InvalidTokenError, MerchantNotFoundError) as e:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.message)
        return

    
    await manager.connect(merchant_id, ws)

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(merchant_id, ws)
        logger.info(f"WS disconnected loop exit: {merchant_id}")
