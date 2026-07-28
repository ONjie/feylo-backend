import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from main import app
from src.utils.database import get_db_session
from src.merchant.models import Merchant
from src.transaction.models import Transaction
from src.wallet.models import Wallet
from tests.conftest import db_session
from src.otp.models import OTP
from src.auth.security import create_access_token


@pytest.mark.asyncio
class TestMerchantRoute:

    base_url = "http://test"

    @pytest.mark.parametrize(
        "merchant_state, use_valid_token, expected_http_status, expected_message",
        [
            pytest.param(
                {"is_verified": True, "is_active": True},
                True,
                status.HTTP_200_OK,
                None,
                id="get_merchant_success"
            ),
            pytest.param(
                {"is_verified": True, "is_active": True},
                False, 
                status.HTTP_400_BAD_REQUEST,
                "Could not validate credentials",
                id="invalid_token"
            ),
            pytest.param(
                {"is_verified": False, "is_active": True},
                True,
                status.HTTP_401_UNAUTHORIZED,
                "Merchant phone number is not verified",
                id="merchant_not_verified"
            ),
            pytest.param(
                {"is_verified": True, "is_active": False},
                True,
                status.HTTP_403_FORBIDDEN,
                "Merchant account is deactivated",
                id="merchant_account_deactivated"
            ),
        ],
    )
    async def test_get_merchant_endpoint(
        self, db_session, merchant_state, use_valid_token, expected_http_status, expected_message):

        app.dependency_overrides[get_db_session] = lambda: db_session

        merchant_id = "merchant_1234"

        merchant = Merchant(
            merchant_id=merchant_id,
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number=f"+220996{expected_http_status}",
            is_verified=merchant_state["is_verified"],
            is_active=merchant_state["is_active"]
        )
        db_session.add(merchant)
        await db_session.commit()

        token_string = create_access_token(merchant_id=merchant_id)
        if not use_valid_token:
            token_string = token_string + "corrupted_signature_data"

        headers = {"Authorization": f"Bearer {token_string}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.get("/api/v1/merchant/profile", headers=headers)  

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
        json_data = response.json()


        if expected_http_status == status.HTTP_200_OK:
            assert json_data["merchant_id"] == merchant.merchant_id
            assert json_data["first_name"] == merchant.first_name
            assert json_data["last_name"] == merchant.last_name
            assert json_data["business_name"] == merchant.business_name
        else:
            assert json_data["detail"] == expected_message
