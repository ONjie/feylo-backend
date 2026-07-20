import pytest, hashlib, hmac, json
from httpx import ASGITransport, AsyncClient
from fastapi import status
from tests.conftest import db_session, redis_client_url
from src.utils.config import settings
from src.transaction.models import Transaction, TxnStatus
from main import app
from src.utils.database import get_db_session
from src.merchant.models import Merchant
from src.wallet.wallet_service import create_wallet
from unittest.mock import AsyncMock, patch, ANY
from datetime import datetime, timedelta, timezone



def generate_signature(body: bytes) -> str: 
    expected_hash = hmac.new(settings.WEBHOOK_SECRET_KEY.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={expected_hash}"


class TestPaymentWebhookRoute:
    base_url = "http://test"

    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "initial_txn_status, is_expired, webhook_payload_status, override_signature, expected_http_status, expected_final_status",
        [
            pytest.param(
                TxnStatus.PENDING, 
                False, 
                "SUCCESS", 
                lambda body: generate_signature(body), 
                status.HTTP_200_OK, 
                TxnStatus.COMPLETED,
                id="successful_payment_workflow"
            ),
            pytest.param(
                TxnStatus.PENDING, 
                False, 
                "FAILED", 
                lambda body: generate_signature(body), 
                status.HTTP_200_OK, 
                TxnStatus.FAILED,
                id="failed_payment_workflow"
            ),
            pytest.param(
                TxnStatus.PENDING, 
                True, 
                "SUCCESS", 
                lambda body: generate_signature(body), 
                status.HTTP_200_OK, 
                TxnStatus.EXPIRED,  
                id="expired_transaction_workflow"
            ),
            pytest.param(
                TxnStatus.PENDING, 
                False, 
                "SUCCESS", 
                lambda body: "sha256=invalid_signature_hash_value", 
                status.HTTP_403_FORBIDDEN, 
                TxnStatus.PENDING,
                id="rejected_bad_signature",
            ),
            pytest.param(
                TxnStatus.COMPLETED, 
                False, 
                "SUCCESS", 
                lambda body: generate_signature(body), 
                status.HTTP_200_OK, 
                TxnStatus.COMPLETED,
                id="ignored_duplicate_webhook"
            ),
        ],
    )
    @patch("src.websocket.websocket_manager.manager.broadcast", new_callable=AsyncMock)
    async def test_receive_webhook(
        self, 
        mock_broadcast,
        db_session, 
        initial_txn_status, 
        is_expired,
        webhook_payload_status, 
        override_signature, 
        expected_http_status,
        expected_final_status
    ):
        app.dependency_overrides[get_db_session] = lambda: db_session

        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
            is_verified=True,
            is_active=True
        )
        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)

        
        if is_expired:
            expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        txn = Transaction(
            status=initial_txn_status,
            merchant_id=merchant.merchant_id,
            amount=100.0,
            net_amount=99.9,
            fee=0.1,
            currency="GMD",
            payment_provider="Wave",
            customer_phone_number="+2201234567",
            expires_at=expires_at
        )
        db_session.add(txn)
        await db_session.commit()
        await db_session.refresh(txn)

        await create_wallet(merchant_id=merchant.merchant_id, session=db_session)

        payload_dict = {
            'transaction_id': txn.id,
            'payment_provider': 'WAVE',
            'amount': 100.0,
            'status': webhook_payload_status,              
            'external_reference': 'WAVE_123',
            'customer_phone_number': '+2203456789'
        }

        raw_json_body = json.dumps(payload_dict).encode("utf-8")
        headers = {"X-Signature": override_signature(raw_json_body)}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post("/api/v1/payments/webhook", content=raw_json_body, headers=headers)

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
        
        await db_session.refresh(txn)
        assert txn.status == expected_final_status

        
        if initial_txn_status == TxnStatus.PENDING:
            if expected_final_status == TxnStatus.COMPLETED:
                mock_broadcast.assert_called_once_with(merchant.merchant_id, ANY)
                called_payload = mock_broadcast.call_args[0][1]
                assert called_payload["event"] == "PAYMENT_RECEIVED"
                
            elif expected_final_status == TxnStatus.EXPIRED:
                mock_broadcast.assert_called_once_with(merchant.merchant_id, ANY)
                called_payload = mock_broadcast.call_args[0][1]
                assert called_payload["event"] == "PAYMENT_EXPIRED"
        else:
            mock_broadcast.assert_not_called()