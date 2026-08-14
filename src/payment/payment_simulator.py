"""
Payment network simulator.
Mimics Wave / AfriMoney / QMoney USSD confirmation delay,
then fires a real signed webhook to our own endpoint.
"""
import asyncio, hmac, hashlib, random, logging, httpx, json, sys
from src.utils.config import settings

logging.basicConfig(
    level=logging.INFO,                                
    format="%(asctime)s [%(levelname)s] %(message)s",  
    handlers=[logging.StreamHandler(sys.stdout)]  
)
logger = logging.getLogger(__name__)


PAYMENT_PROVIDER_REFS = {
    "wave":       lambda: f"WAVE-{random.randint(100_000, 999_999)}",
    "afrimoney":  lambda: f"AFR-{random.randint(100_000, 999_999)}",
    "qmoney":     lambda: f"QM-{random.randint(100_000, 999_999)}",
    "aps":     lambda: f"APS-{random.randint(100_000, 999_999)}"
}


async def execute_simulated_webhook(
    txn_id: str,
    payment_provider: str,
    amount: float,
    customer_phone_number: str,
    customer_full_name: str
) -> None:
    delay = random.uniform(2.0, 4.5)
    logger.info(f"[SIM] {payment_provider} USSD delay: {delay:.1f}s for {txn_id}")
    await asyncio.sleep(delay)

    payload = {
        "transaction_id": txn_id,
        "payment_provider": payment_provider.title(),
        "amount": amount,
        "status": "SUCCESS",
        "external_reference": PAYMENT_PROVIDER_REFS.get(payment_provider, lambda: "REF-000000")(),
        "customer_phone_number": customer_phone_number,
        "customer_full_name": customer_full_name,
    }
    raw = json.dumps(payload).encode()

    sig = hmac.new(
        settings.WEBHOOK_SECRET_KEY.encode(), raw, hashlib.sha256
    ).hexdigest()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.BASE_URL}/api/v1/payments/webhook",
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": f"sha256={sig}",
                },
                timeout=10.0,
            )
            logger.info(f"[SIM] Webhook response: {resp.status_code} for {txn_id}")
    except Exception as exc:
        logger.error(f"[SIM] Webhook delivery failed for {txn_id}: {exc}")
