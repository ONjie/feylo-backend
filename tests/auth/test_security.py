import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from jose import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.exceptions import InvalidTokenError
from src.merchant.models import Merchant
from src.utils.config import settings
from src.auth.security import (
    hash_pin_code,
    verify_pin_code,
    create_access_token,
    decode_access_token,
    get_current_merchant,
    verify_signature
)
from tests.conftest import db_session
import hmac, hashlib


def test_hash_and_verify_pin_code():
    raw_pin = '1234'
    hashed_pin_code = hash_pin_code(raw_pin)

    assert hashed_pin_code != raw_pin
    assert verify_pin_code(raw_pin, hashed_pin_code) is True
    assert verify_pin_code("5678", hashed_pin_code) is False


def test_create_access_token():
    merchant_id = 'merchant_1234'

    access_token = create_access_token(merchant_id)

    payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert payload['sub'] == merchant_id
    assert "iat" in payload
    assert "exp" in payload


@pytest.mark.parametrize(
    'token_generator, expected_merchant_id, expected_exception, expected_message',
    [
        pytest.param(
            lambda: jwt.encode(
                {
                    "sub": "merchant_123", 
                    "iat": datetime.now(timezone.utc), 
                    "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
                },
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            ),
            "merchant_123", 
            None,
            None,
            id="decode_success"
        ),
        pytest.param(
            lambda: jwt.encode(
                {"sub": ""}, 
                settings.JWT_SECRET_KEY, 
                algorithm=settings.JWT_ALGORITHM
            ),
            None,
            InvalidTokenError,
            "Invalid token payload",
            id="failure_missing_sub_claim"
        ),
        pytest.param(
            lambda: jwt.encode(
                {
                    "sub": "123", 
                    "exp": datetime.now(timezone.utc) - timedelta(days=settings.JWT_EXPIRE_DAYS)
                }, 
                settings.JWT_SECRET_KEY, 
                algorithm=settings.JWT_ALGORITHM
            ),
            None,
            InvalidTokenError,
            "Could not validate credentials",
            id="failure_expired_jwt_token"
        ),
        pytest.param(
            lambda: "completely_invalid_token_string",
            None,
            InvalidTokenError,
            "Could not validate credentials",
            id="failure_malformed_token_string"
        ),
    ]
)
def test_decode_access_token_flows(
    token_generator, expected_merchant_id, expected_exception, expected_message
):
    token = token_generator()

    if expected_exception:
        with pytest.raises(expected_exception) as exc:
            decode_access_token(token)
        
        assert expected_message in str(exc.value)
    
    else:
        extracted_id = decode_access_token(token)
        
        assert extracted_id == expected_merchant_id


@pytest.mark.asyncio
class TestGetCurrentMerchantDependency:

    @pytest.mark.parametrize(
        "token_generator, merchant_state, expected_status_code, expected_detail",
        [
            pytest.param(
                lambda merchant_id: create_access_token(merchant_id),
                {"is_verified": True, "is_active": True},
                None,
                None,
                id="get_current_merchant_success"
            ),
            pytest.param(
                lambda merchant_id: create_access_token(""),
                None,
                status.HTTP_400_BAD_REQUEST,
                "Invalid token payload",
                id="invalid_token_payload"
            ),
            pytest.param(
                lambda merchant_id: create_access_token(merchant_id),
                None,  
                status.HTTP_404_NOT_FOUND,
                "Merchant missing_merchant_id not found.", 
                id="_merchant_not_found"
            ),
            pytest.param(
                lambda merchant_id: create_access_token(merchant_id),
                {"is_verified": False, "is_active": True},
                status.HTTP_401_UNAUTHORIZED,
                "Merchant phone number is not verified",
                id="merchant_not_verified"
            ),
            pytest.param(
                lambda merchant_id: create_access_token(merchant_id),
                {"is_verified": True, "is_active": False},
                status.HTTP_403_FORBIDDEN,
                "Merchant account is deactivated",
                id="mechant_account_deactivated"
            ),
        ],
    )
    async def test_get_current_merchant_states(
        self, db_session, token_generator, merchant_state, expected_status_code, expected_detail
    ):
        merchant_id = "missing_merchant_id" if merchant_state is None else "merchant_123"
        
        if merchant_state:
            new_merchant = Merchant(
                merchant_id=merchant_id,
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number="+2202233445",
                is_verified=merchant_state["is_verified"],
                is_active=merchant_state["is_active"]
            )
            db_session.add(new_merchant)
            await db_session.commit()

        valid_token = token_generator(merchant_id)
        credentials_mock = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token)


        if expected_status_code:
            with pytest.raises(HTTPException) as exc:
                await get_current_merchant(cred=credentials_mock, session=db_session)
            
            assert exc.value.status_code == expected_status_code
            assert exc.value.detail == expected_detail
        else:
            result = await get_current_merchant(cred=credentials_mock, session=db_session)
            assert result.merchant_id == merchant_id
            assert result.is_active is True
            assert result.is_verified is True



def get_valid_header(body: bytes) -> str:
    hash_val = hmac.new(settings.WEBHOOK_SECRET_KEY.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={hash_val}"

@pytest.mark.parametrize(
     "raw_body, get_signature_header, expected_result",
    [
        pytest.param(
            b'{"merchant_id": "MERCH_1234"}', 
            lambda: get_valid_header(b'{"merchant_id": "MERCH_1234"}'), 
            True, 
            id="valid_payload"
            ),
        pytest.param(
            b"", 
            lambda: get_valid_header(b""), 
            True, 
            id="valid_empty_payload"
            ),
        pytest.param(
            b'{"merchant_id": "MERCH_1234"}', 
            lambda: "sha256=incorrect_hash_string", 
            False, 
            id="bad_signature_hash"),
        pytest.param(
            b'{"merchant_id": "MERCH_1234"}', 
            lambda: get_valid_header(b'{"merchant_id": "MERCH_2222"}'), 
            False, 
            id="tampered_payload_body"
            ),
        pytest.param(
            b'{"merchant_id": "MERCH_1234"}', 
            lambda: get_valid_header(b'{"merchant_id": "MERCH_1234"}').replace("sha256=", ""), 
            False, 
            id="missing_prefix"
            ),
        pytest.param(
            b'{"merchant_id": "MERCH_1234"}', 
            lambda: "", 
            False, 
            id="blank_header"
            ),
    ],
)
def test_verify_signature(raw_body, get_signature_header, expected_result):
    header_string = get_signature_header()
    assert verify_signature(raw_body, header_string) is expected_result