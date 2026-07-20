import json
import logging
from collections import defaultdict
from fastapi import WebSocket
import sys
import asyncio
import redis.asyncio as aioredis
from redis import asyncio as aioredis
from src.utils.config import settings

logging.basicConfig(
    level=logging.INFO,                                
    format="%(asctime)s [%(levelname)s] %(message)s",  
    handlers=[logging.StreamHandler(sys.stdout)]  
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    
    def __init__(self, redis_url: str = settings.REDIS_URL) -> None:
        self.active: dict[str, list[WebSocket]] = defaultdict(list)
        self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        self._listen_task: asyncio.Task | None = None

    async def start_listening(self) -> None:
        if self._listen_task is None or self._listen_task.done():
            self._listen_task = asyncio.create_task(self._redis_listener())
            logger.info("Redis Pub/Sub background listener attached.")

    async def connect(self, merchant_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active[merchant_id].append(ws)
        logger.info(f"WS connected: {merchant_id} ({len(self.active[merchant_id])} local socket(s))")

    def disconnect(self, merchant_id: str, ws: WebSocket) -> None:
        try:
            self.active[merchant_id].remove(ws)
            if not self.active[merchant_id]:
                del self.active[merchant_id]
            logger.info(f"WS disconnected: {merchant_id}")
        except ValueError:
            pass

    async def broadcast(self, merchant_id: str, data: dict) -> None:
        payload = json.dumps({"merchant_id": merchant_id, "data": data})
        await self.redis_client.publish("merchant_payment_notifications", payload)

    async def _local_broadcast(self, merchant_id: str, data: dict) -> None:
        payload = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in self.active.get(merchant_id, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(merchant_id, ws)

    async def _redis_listener(self) -> None:
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("merchant_payment_notifications")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    m_id = payload.get("merchant_id")
                    data = payload.get("data")
                    
                    if m_id in self.active:
                        await self._local_broadcast(m_id, data)
        except asyncio.CancelledError:
            await pubsub.unsubscribe("merchant_payment_notifications")
        except Exception as e:
            logger.error(f"Redis link dropped unexpectedly: {e}")

    async def stop_listening(self) -> None:
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            logger.info("Redis Pub/Sub background listener stopped.")


    def connected_count(self) -> int:
        return sum(len(v) for v in self.active.values())

manager = ConnectionManager()
