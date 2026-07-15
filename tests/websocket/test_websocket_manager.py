import pytest
import asyncio
from unittest.mock import AsyncMock
from src.websocket.websocket_manager import ConnectionManager
from tests.conftest import redis_container
import json


@pytest.mark.asyncio
class TestWebsocketManager:

    async def test_distributed_redis_broadcasting(self, redis_container):
        
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(redis_container.port)
        test_redis_url = f"redis://{host}:{port}/0"
        
        manager_instance = ConnectionManager(redis_url=test_redis_url)
        await manager_instance.start_listening()
        
        mock_ws = AsyncMock()
        merchant_id = "merchant_test_id"
        
        
        manager_instance.active[merchant_id].append(mock_ws)
        
        await asyncio.sleep(0.1)

        test_payload = {'event': 'new_payment', 'amount': 150.00}
        await manager_instance.broadcast(merchant_id, test_payload)
        
        await asyncio.sleep(0.2)

        mock_ws.send_text.assert_called_once()
        actual_sent_string = mock_ws.send_text.call_args[0][0]
        actual_sent_dict = json.loads(actual_sent_string)
        
        assert test_payload.get('event') == actual_sent_dict.get('event')
        assert test_payload.get('amount') == actual_sent_dict.get('amount')
        
        if manager_instance._listen_task:
            manager_instance._listen_task.cancel()