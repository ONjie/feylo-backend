import pytest
import asyncio
from fastapi import status
from fastapi.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient
from src.websocket.websocket_manager import ConnectionManager
from src.auth.exceptions import InvalidTokenError
from src.merchant.exceptions import MerchantNotFoundError
from src.merchant.models import Merchant
from src.auth.security import create_access_token
from src.websocket.websocket_routes import merchant_websocket_endpoint
from tests.conftest import db_session
from src.utils.database import get_db_session
from main import app
from unittest.mock import AsyncMock, patch


class TestWebsocketRoute:

    @pytest.mark.parametrize(
        "merchant_id, token_merchant_id, merchant_state, merchant_exists, expected_close_code",
        [
            pytest.param(
                "MERCH_1234",
                "MERCH_1234",
                {"is_active": True, "is_verified": True},
                True,
                None,
                id="merchant_websocket_endpoint_success",
            ),
            pytest.param(
                "MERCH_1234",
                "MERCH_2345",
                {"is_active": True, "is_verified": True},
                True,
                status.WS_1008_POLICY_VIOLATION,
                id="wrong_merchant_id_failure",
            ),
            pytest.param(
                "MERCH_1234",
                "MERCH_1234",
                {"is_active": True, "is_verified": False},
                True,
                status.WS_1008_POLICY_VIOLATION,
                id="merchant_not_verified_failure",
            ),
            pytest.param(
                "MERCH_9999",
                "MERCH_9999",
                {"is_active": True, "is_verified": True},
                False,
                status.WS_1008_POLICY_VIOLATION,
                id="merchant_not_found_failure",
            ),
        ],
    )
    def test_merchant_websocket_endpoint(
        self,
        merchant_id,
        token_merchant_id,
        merchant_state,
        merchant_exists,
        expected_close_code,
    ):
        token_string = create_access_token(
            merchant_id=token_merchant_id
        )

        merchant = Merchant(
            merchant_id=merchant_id,
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202233445",
            is_verified=merchant_state["is_verified"],
            is_active=merchant_state["is_active"],
        )

        get_merchant_mock = AsyncMock()

        if merchant_exists:
            get_merchant_mock.return_value = merchant
        else:
            get_merchant_mock.side_effect = MerchantNotFoundError()

        with patch(
            "src.websocket.websocket_routes.get_merchant",
            get_merchant_mock,
        ):
                client = TestClient(app=app)

                if expected_close_code is None:
                    with client.websocket_connect(
                        f"/ws/merchant/{merchant_id}?token={token_string}"
                    ) as ws:
                        ws.send_text("ping")
                        assert ws.receive_text() == "pong"

                else:
                    with pytest.raises(WebSocketDisconnect) as exc:
                        with client.websocket_connect(
                            f"/ws/merchant/{merchant_id}?token={token_string}"
                        ) as ws:
                            ws.receive_text()

                    assert exc.value.code == expected_close_code