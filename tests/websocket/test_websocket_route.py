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
from src.websocket.websocket_route import merchant_websocket_endpoint
from tests.conftest import db_session
from src.utils.database import get_db_session
from main import app
from unittest.mock import AsyncMock, patch


"""@pytest.mark.asyncio
class TestWebsocketRoute:

    @pytest.mark.parametrize(
        'merchant_id, token_merchant_id, merchant_state, expected_close_code',
        [
            pytest.param(
                'MERCH_1234',
                'MERCH_1234',
                {'is_active': True, 'is_verified': True},
                None,
                id='merchant_websocket_endpoint_success'
            ),
            pytest.param(
                'MERCH_1234',
                'MERCH_2345',
                {'is_active': True, 'is_verified': True},
                status.WS_1008_POLICY_VIOLATION,
                id='wrong_merchant_id_failure'
            ),
            pytest.param(
                'MERCH_1234',
                'MERCH_1234',
                {'is_active': True, 'is_verified': False},
                status.WS_1008_POLICY_VIOLATION,
                id='merchant_not_verified_failure'
            ),
            pytest.param(
                'MERCH_9999', 
                'MERCH_9999',
                {'is_active': True, 'is_verified': True},
                status.WS_1008_POLICY_VIOLATION,
                id='merchant_not_found_failure'
            )
        ]
    )


    async def test_merchant_websocket_endpoint(
        self, db_session, merchant_id, token_merchant_id, merchant_state, expected_close_code, request
     ):
        
        if "merchant_not_found_failure" in request.node.name:
            
            token_string = create_access_token(merchant_id=token_merchant_id)
        else:
            merchant = Merchant(
                merchant_id=merchant_id,
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number="+2202233445",
                is_verified=merchant_state["is_verified"],
                is_active=merchant_state["is_active"]
            )
            db_session.add(merchant)
            await db_session.commit()
            await db_session.refresh(merchant)
            token_string = create_access_token(merchant_id=token_merchant_id)

        app.dependency_overrides[get_db_session] = lambda: db_session

        client = TestClient(app=app)
        actual_close_code = None

        try:
            with client.websocket_connect(f"/ws/merchant/{merchant_id}?token={token_string}") as ws:
                if expected_close_code is None:
                    ws.send_text("ping")
                    assert ws.receive_text() == "pong"
                else:
                    ws.receive_text()

        except WebSocketDisconnect as e:
            print(f'data: {e}')
            # Capture the exact standard code returned by the handshake rejection
            actual_close_code = e.code
        except Exception as e:
            print(f'data: {e}')
            pass

        if expected_close_code is not None:
            assert actual_close_code == expected_close_code

        app.dependency_overrides.clear()

"""


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
            "src.websocket.websocket_route.get_merchant",
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
                    with pytest.raises(WebSocketDisconnect) as exc_info:
                        with client.websocket_connect(
                            f"/ws/merchant/{merchant_id}?token={token_string}"
                        ) as ws:
                            ws.receive_text()

                    assert exc_info.value.code == expected_close_code