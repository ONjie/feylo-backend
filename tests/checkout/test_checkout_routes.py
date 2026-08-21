import pytest
import uuid
from httpx import ASGITransport, AsyncClient
from fastapi import status
from datetime import datetime, timezone, timedelta
from tests.conftest import db_session
from src.transaction.models import Transaction, TxnStatus
from src.merchant.models import Merchant
from src.checkout.schemas import CheckoutPayRequest
from main import app
from src.utils.database import get_db_session


class TestCheckoutRoutes:
    base_url = "http://test"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "txn_status, is_expired, expected_http_status, expected_detail",
        [
            pytest.param(
                TxnStatus.PENDING, 
                False,
                status.HTTP_200_OK, 
                None,
                id="checkout_success"
            ),
            pytest.param(
                TxnStatus.COMPLETED, 
                False,
                status.HTTP_403_FORBIDDEN, 
                "This payment has already been completed.",
                id="payment_completed_failure"
            ),
            pytest.param(
                TxnStatus.FAILED, 
                False,
                status.HTTP_403_FORBIDDEN, 
                "This payment link has expired.",
                id="failed_payment_failure"
            ),
            pytest.param(
                TxnStatus.EXPIRED, 
                False,
                status.HTTP_403_FORBIDDEN, 
                "This payment link has expired.",
                id="expired_payment_failure"
            ),
            pytest.param(
                None, 
                False, 
                status.HTTP_404_NOT_FOUND, 
                f"Transaction 45310bea-8baf-4f98-8370-f2837094a01f not found", 
                id="transaction_not_found"
            ),
        ],
    )
    async def test_checkout_page_lifecycle(
        self, 
        db_session, 
        txn_status, 
        is_expired, 
        expected_http_status, 
        expected_detail
    ):
        app.dependency_overrides[get_db_session] = lambda: db_session

        txn_id = "45310bea-8baf-4f98-8370-f2837094a01f"

        if txn_status is not None:
            merchant = Merchant(
                first_name="Muhammed O", 
                last_name="Njie", 
                business_name="Njie", 
                phone_number="+2207777777",
                is_verified=True, 
                is_active=True
            )
            db_session.add(merchant)
            await db_session.commit()

            txn = Transaction(
                status=txn_status,
                merchant_id=merchant.merchant_id,
                amount=250.0, 
                net_amount=245.0, 
                fee=5.0,
                currency="GMD", 
                payment_provider="Wave",
                customer_phone_number="+2209998881",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5) if is_expired else None
            )
            db_session.add(txn)
            await db_session.commit()
            await db_session.refresh(txn)
            txn_id = txn.id

        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.get(f"/api/v1/checkout/{txn_id}")

        app.dependency_overrides.clear()

        
        assert response.status_code == expected_http_status
        json_data = response.json()
        if expected_detail is None:
            assert json_data['id'] == txn_id
            assert json_data['business_name'] == merchant.business_name

        else:
            assert json_data["detail"] == expected_detail 
  

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "txn_status, chosen_provider, customer_phone_number, expected_http_status, expected_detail",
        [
            pytest.param(
                TxnStatus.PENDING, 
                "wave", 
                "+2203333333", 
                status.HTTP_200_OK, 
                "Check your phone for PIN prompt",
                id="successful_payment_initiation"
            ),
            pytest.param(
                TxnStatus.PENDING, 
                "INVALID_PROVIDER", 
                "+2203333333", 
                status.HTTP_400_BAD_REQUEST, 
                "Unknown provider",
                id="invalid_provider_failure"
            ),
            pytest.param(
                TxnStatus.COMPLETED, 
                "qmoney", 
                "+2203333333", 
                status.HTTP_409_CONFLICT, 
                "Transaction is no longer pending",
                id="payment_completed_failure"
            ),
            pytest.param(
                None, 
                "wave", 
                "+2203333333", 
                status.HTTP_404_NOT_FOUND, 
                "not found",
                id="transaction_not_found_failure"
            ),
        ],
    )
    async def test_initiate_payment_endpoint(
        self, 
        db_session, 
        txn_status, 
        chosen_provider, 
        customer_phone_number, 
        expected_http_status, 
        expected_detail
    ):
        app.dependency_overrides[get_db_session] = lambda: db_session
        target_tx_id = str(uuid.uuid4())

        customer_full_name = 'Ablie Jallow'

        if txn_status is not None:
            merchant = Merchant(
                first_name="Muhammed O", 
                last_name="Njie", 
                business_name="Njie Store", 
                phone_number="+2205555555",
                is_verified=True, 
                is_active=True
            )
            db_session.add(merchant)
            await db_session.commit()

            txn = Transaction(
                status=txn_status,
                merchant_id=merchant.merchant_id,
                amount=500.0, 
                net_amount=490.0, 
                fee=10.0,
                currency="GMD", 
                payment_provider="Wave",
                customer_phone_number="+2201112223",
                customer_full_name=customer_full_name
            )
            db_session.add(txn)
            await db_session.commit()
            await db_session.refresh(txn)
            target_tx_id = txn.id

        
        payload = {
            "payment_provider": chosen_provider, 
            "customer_phone_number": customer_phone_number, 
            "customer_full_name": customer_full_name
            }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post(f"/api/v1/checkout/{target_tx_id}/pay", json=payload)

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
        if expected_http_status == status.HTTP_200_OK:
            assert response.json()["status"] == "processing"
            assert response.json()["message"] == expected_detail 
        else:
            assert expected_detail in response.json()["detail"]