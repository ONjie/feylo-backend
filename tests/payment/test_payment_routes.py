import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from fastapi import status
from main import app
from src.utils.database import get_db_session
from src.merchant.models import Merchant
from src.transaction.models import Transaction
from src.wallet.models import Wallet
from tests.conftest import db_session
from src.payment.payment_routes import generate_qr_code_endpoint
from src.utils.config import settings
from src.auth.security import create_access_token


@pytest.mark.asyncio
class TestPaymentRoute:

    base_url = "http://test"


    @pytest.mark.parametrize(
        'payload, fee, net_amount, expected_amount',
        [
            pytest.param({'amount':100.00}, 0.5, 99.50, 100.00, id='generate_qr_code_endpoint_success_one'),
            pytest.param({'amount':150.50}, 0.5, 150, 150.50, id='generate_qr_code_endpoint_success_two'),
        ]
    )

    async def test_generate_qr_code_endpoint(
        self, db_session, payload, fee, net_amount, expected_amount):

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
    

        token_string = create_access_token(merchant_id=merchant.merchant_id)

        headers = {"Authorization": f"Bearer {token_string}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post("/api/v1/payments/generate-qr-code", json=payload, headers=headers)
        
        app.dependency_overrides.clear()
        print(response.json())

        assert response.status_code == status.HTTP_201_CREATED

        json_data = response.json()

        assert json_data["amount"] == expected_amount
        assert json_data["currency"] == "GMD"
        