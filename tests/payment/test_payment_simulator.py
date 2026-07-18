import json
import pytest
import respx
import hmac
import hashlib
import asyncio
from httpx import Response
from src.payment.payment_simulator import execute_simulated_webhook, PAYMENT_PROVIDER_REFS
from src.utils.config import settings





@pytest.mark.asyncio
class TestPaymentSimulator:

    async def fast_sleep(*args, **kwargs):
        return


    @respx.mock
    @pytest.mark.parametrize(
        "input_provider, expected_title_provider, input_amount, server_response_status, expected_log_msg",
        [
            pytest.param(
                "wave", "Wave", 250.0, 200, "[SIM] Webhook response: 200", 
                id="successful_wave_webhook"
            ),
            pytest.param(
                "afrimoney", "Afrimoney", 100.5, 200, "[SIM] Webhook response: 200", 
                id="successful_afrimoney_webhook"
            ),
            pytest.param(
                "qmoney", "Qmoney", 75.0, 200, "[SIM] Webhook response: 200", 
                id="successful_qmoney_webhook"
            ),
            pytest.param(
                "aps", "Aps", 500.0, 200, "[SIM] Webhook response: 200", 
                id="successful_aps_webhook"
            ),
            pytest.param(
                "wave", "Wave", 10.0, 500, "[SIM] Webhook response: 500", 
                id="failed_webhook_server_error"
            ),
        ]
    )
    async def test_execute_simulated_webhook_scenarios(
        self,
        input_provider,
        expected_title_provider,
        input_amount,
        server_response_status,
        expected_log_msg
    ):
        original_sleep = asyncio.sleep
        asyncio.sleep = self.fast_sleep

        txn_id = "TXN_SIM_9999"
        customer_phone_number = "+2201234567"
        

        expected_url = f"{settings.BASE_URL}/api/v1/payments/webhook"

        route = respx.post(expected_url).mock(return_value=Response(server_response_status))

        try:
            
            await execute_simulated_webhook(
                txn_id=txn_id,
                payment_provider=input_provider,
                amount=input_amount,
                customer_phone_number=customer_phone_number
            )
        finally:
           
            asyncio.sleep = original_sleep

        
        assert route.called
        assert route.call_count == 1

        last_request = route.calls.last.request
        request_payload = json.loads(last_request.content.decode("utf-8"))

        
        assert request_payload["transaction_id"] == txn_id
        assert request_payload["payment_provider"] == expected_title_provider
        assert request_payload["amount"] == input_amount
        assert request_payload["status"] == "SUCCESS"
        assert request_payload["customer_phone_number"] == customer_phone_number
        assert "external_reference" in request_payload

        
        signature_header = last_request.headers.get("X-Signature")
        assert signature_header is not None
        assert signature_header.startswith("sha256=")

        
        actual_hash = signature_header.replace("sha256=", "")
        expected_hash = hmac.new(
            settings.WEBHOOK_SECRET_KEY.encode(),
            last_request.content,
            hashlib.sha256
        ).hexdigest()
        assert actual_hash == expected_hash


