import pytest
import hashlib
from jose import jwt
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from fastapi import status
from main import app
from src.utils.database import get_db_session
from src.merchant.models import Merchant
from src.transaction.models import Transaction
from src.wallet.models import Wallet
from tests.conftest import db_session
from src.otp.models import OTP
from src.utils.config import settings
from src.auth.security import create_access_token
from src.wallet.wallet_service import create_wallet


@pytest.mark.asyncio
class TestAuthRoutes:

    base_url = "http://test"

    @pytest.mark.parametrize(
        'payload, should_pre_seed, expected_http_status, expected_detail_message',
        [
            pytest.param(
                {
                    "first_name": "Muhammed",
                    "last_name": "Njie",
                    "business_name": "Njie Store",
                    "phone_number": "+2202233445"
                },
                False,
                status.HTTP_201_CREATED,
                "OTP sent — check your phone",
                id="registration_success"
            ),
            pytest.param(
                {
                    "first_name": "Muhammed",
                    "last_name": "Njie",
                    "business_name": "Njie Store",
                    "phone_number": "+2202233445"
                },
                True,
                status.HTTP_409_CONFLICT,
                "already exists. — use /auth/login instead",
                id="registration_merchant_exists_failure"
            ),
            
        ]
    )
    async def test_register_endpoint(
        self, db_session, payload, should_pre_seed, expected_http_status, expected_detail_message):
        app.dependency_overrides[get_db_session] = lambda: db_session


        if should_pre_seed:
            pre_seeded_merchant = Merchant(
                merchant_id="merchant_1234",
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number=payload["phone_number"],
            )
            db_session.add(pre_seeded_merchant)
            await db_session.commit()

            await create_wallet(merchant_id=pre_seeded_merchant.merchant_id, session=db_session)
            await db_session.commit()


        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == expected_http_status
        if expected_http_status == status.HTTP_201_CREATED:
            assert response.json()["message"] == expected_detail_message


    @pytest.mark.parametrize(
        'payload, should_pre_seed, expected_http_status, expected_detail_message',
        [
            pytest.param(
                {"phone_number": "+2202233445"},
                True,
                status.HTTP_200_OK,
                'OTP sent — check your phone',
                id='login_success'
            ), pytest.param(
                {"phone_number": "+2202244556"},
                False, 
                status.HTTP_404_NOT_FOUND,
                "Merchant +2202244556 not found.", 
                id="login_failure_merchant_not_found"
            ),
            
            pytest.param(
                {"phone_number": "+2201111111"}, 
                False,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                'Value error, Invalid Gambian phone number format. Must be a valid 7-digit local number or include the 220 prefix.',
                id="login_failure_schema_validation"
            ),
        ]
    )
    async def test_login_endpoint(
        self, db_session, payload, should_pre_seed, expected_http_status, expected_detail_message):
        app.dependency_overrides[get_db_session] = lambda: db_session


        if should_pre_seed:
            pre_seeded_merchant = Merchant(
                merchant_id="merchant_1234",
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number=payload['phone_number'],
            )
            db_session.add(pre_seeded_merchant)
            await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post('/api/v1/auth/login', json=payload)
        

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
       
        
        json_data = response.json()
        print(json_data)
        if expected_http_status == status.HTTP_200_OK:
            assert json_data["message"] == expected_detail_message

        elif expected_http_status == status.HTTP_404_NOT_FOUND:
            assert json_data['detail'] == expected_detail_message

        elif expected_http_status == status.HTTP_422_UNPROCESSABLE_CONTENT:
            assert json_data['detail'][0]['msg'] == expected_detail_message


    @pytest.mark.parametrize(
        'payload, seed_otp_attempts, is_expired, expected_http_status, expected_detail_message',
        [
            pytest.param(
                {
                    "phone_number": "+2202233445",
                    "submitted_otp": "123456"
                },
                0,
                False,
                status.HTTP_200_OK,
                None,
                id="verify_otp_success"
            ),
            pytest.param(
                {
                    "phone_number": "+2202233445",
                    "submitted_otp": "123456"
                }, 
                0, 
                True, 
                status.HTTP_404_NOT_FOUND, 
                "The verification code has expired.", 
                id="otp_code_expired"
            ),
            pytest.param(
                {
                    "phone_number": "+2202233445",
                    "submitted_otp": "123678"
                },
                0, 
                False, 
                status.HTTP_404_NOT_FOUND, 
                "Invalid verification code.", 
                id="invalid_otp_code"
            ),

        ]
    )
    async def test_verify_otp_endpoint(
        self, db_session, payload, seed_otp_attempts, is_expired, expected_http_status, expected_detail_message):
        app.dependency_overrides[get_db_session] = lambda: db_session

        merchant_id = 'merchant_1234'
        raw_secret_otp = "123456"


        merchant = Merchant(
            merchant_id=merchant_id,
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number=payload['phone_number'],
            is_verified=False,  
            is_active=True
        )
        db_session.add(merchant)


        time_offset = -timedelta(minutes=5) if is_expired else timedelta(minutes=10)
        otp_expiry = datetime.now(timezone.utc) + time_offset
     
        hashed_otp = hashlib.sha256(raw_secret_otp.encode("utf-8")).hexdigest()
        otp_record = OTP(
            phone_number=payload['phone_number'],
            otp_hash=hashed_otp,
            expiry_time=otp_expiry,
            otp_attempts=seed_otp_attempts
        )
        db_session.add(otp_record)
        await db_session.commit()


        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post('/api/v1/auth/verify-otp', json=payload)

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
        json_data = response.json()

        if expected_http_status == status.HTTP_200_OK:
            assert "access_token" in json_data
            assert json_data["merchant_id"] == merchant_id

            decoded_jwt = jwt.decode(
                json_data["access_token"], 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            assert decoded_jwt["sub"] == merchant_id

            await db_session.refresh(merchant)
            assert merchant.is_verified is True

        else:
            assert json_data["detail"] == expected_detail_message


    @pytest.mark.parametrize(
        'payload, should_pre_seed, expected_http_status, expected_detail_message',
        [
            pytest.param(
                {"phone_number": "+2202233445"},
                True,
                status.HTTP_200_OK,
                'OTP sent — check your phone',
                id='resend_otp_success'
            ), pytest.param(
                {"phone_number": "+2202244556"},
                False, 
                status.HTTP_404_NOT_FOUND,
                "Merchant +2202244556 not found.", 
                id="resend_otp_failure_merchant_not_found"
            ),
            
            pytest.param(
                {"phone_number": "+2201111111"}, 
                False,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                'Value error, Invalid Gambian phone number format. Must be a valid 7-digit local number or include the 220 prefix.',
                id="resend_otp_failure_schema_validation"
            ),
        ]
    )
    async def test_resend_otp_endpoint(
        self, db_session, payload, should_pre_seed, expected_http_status, expected_detail_message):
        app.dependency_overrides[get_db_session] = lambda: db_session


        if should_pre_seed:
            pre_seeded_merchant = Merchant(
                merchant_id="merchant_1234",
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number=payload['phone_number'],
            )
            db_session.add(pre_seeded_merchant)
            await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.post('/api/v1/auth/resend-otp', json=payload)
        

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
       
        
        json_data = response.json()
        print(json_data)
        if expected_http_status == status.HTTP_200_OK:
            assert json_data["message"] == expected_detail_message

        elif expected_http_status == status.HTTP_404_NOT_FOUND:
            assert json_data['detail'] == expected_detail_message

        elif expected_http_status == status.HTTP_422_UNPROCESSABLE_CONTENT:
            assert json_data['detail'][0]['msg'] == expected_detail_message

    
    @pytest.mark.parametrize(
        "merchant_state, use_valid_token, expected_http_status, expected_message",
        [
            pytest.param(
                {"is_verified": True, "is_active": True},
                True,
                status.HTTP_200_OK,
                'authenticated',
                id="check_auth_success"
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
    async def test_check_auth_status_endpoint(
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
            response = await client.get("/api/v1/auth/status", headers=headers)  

        app.dependency_overrides.clear()

        assert response.status_code == expected_http_status
        json_data = response.json()


        if expected_http_status == status.HTTP_200_OK:
            assert json_data["status"] == expected_message
        else:
            assert json_data["detail"] == expected_message
