import pytest
from sqlalchemy import select
from tests.conftest import db_session
from src.transaction.transaction_service import (
    create_pending_transaction, 
    get_transaction_by_id,
    complete_transaction
    )
from src.transaction.models import Transaction, TxnStatus
from src.merchant.models import Merchant
from src.wallet.models import Wallet
from src.transaction.exceptions import TransactionNotFoundError
from datetime import datetime, timezone, timedelta
from src.utils.config import settings
from src.payment.schemas import WebhookPayload


@pytest.mark.asyncio
class TestTransactionService:


    @pytest.mark.parametrize(
        'amount, expected_fee, expected_net_amount',
        [pytest.param(
            50, 0.50, 49.50, id="create_pending_transaction_success_one"
        ),
        pytest.param(
            150, 1.50, 148.50, id="create_pending_transaction_success_two"
        )]
    )
    async def test_create_pending_transaction(
        self, db_session, amount, expected_fee, expected_net_amount):

        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )

        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)


        result = await create_pending_transaction(
            merchant_id=merchant.merchant_id,
            amount=amount,
            session=db_session
        )

        assert isinstance(result, Transaction)
        assert result.merchant_id == merchant.merchant_id
        assert result.amount == amount
        assert result.net_amount == expected_net_amount
        assert result.fee == expected_fee


    @pytest.mark.parametrize(
        'transaction_exist, amount, fee, net_amount, expected_exception',
        [
            pytest.param(
                True,
                50.0,
                0.50,
                49.50,
                None,
                id="get_transaction_by_id_success"
            ),
            pytest.param(
                False,
                50.0,
                0.50,
                49.50,
                TransactionNotFoundError,
                id="get_transaction_by_id_failure"
            ), 
        ]
    )
    async def test_get_transaction_by_id(
        self, db_session, transaction_exist, amount, fee, net_amount, expected_exception):

        transaction_id = None
        if transaction_exist:
            merchant = Merchant(
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number="+2202234567",
            )

            db_session.add(merchant)
            await db_session.commit()
            await db_session.refresh(merchant)

            txn = Transaction(
                merchant_id=merchant.merchant_id,
                amount=amount,
                fee=fee,
                net_amount=net_amount,
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=settings.QR_EXPIRY_MINUTES),
            )
            db_session.add(txn)
            await db_session.commit()
            await db_session.refresh(txn)

            transaction_id = txn.id


            result = await get_transaction_by_id(transaction_id=transaction_id, session=db_session)

            assert isinstance(result, Transaction)
            assert result.id == transaction_id
            assert result.merchant_id == merchant.merchant_id
            assert result.amount == amount
            assert result.net_amount == net_amount
            assert result.fee == fee

        else:
            with pytest.raises(expected_exception) as exc:
                await get_transaction_by_id(transaction_id=transaction_id, session=db_session)
            assert f"Transaction {transaction_id} not found" in str(exc.value)
            

    @pytest.mark.parametrize(
        ' amount, fee, net_amount',
        [
            pytest.param(
                50.0,
                0.50,
                49.50,
                id="complete_transaction_success"
            )
        ]
    )
    async def test_complete_transaction(
        self, db_session, amount, fee, net_amount):

        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )

        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)

        txn = Transaction(
            merchant_id=merchant.merchant_id,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.QR_EXPIRY_MINUTES),
        )
        db_session.add(txn)
        await db_session.commit()
        await db_session.refresh(txn)

        payload = WebhookPayload(
            transaction_id=txn.id,
            payment_provider="WAVE",
            amount=amount,
            status=TxnStatus.COMPLETED,
            external_reference='external_reference',
            customer_phone_number="+2202222222"
        )


        result = await complete_transaction(txn=txn, payload=payload, session=db_session)

        assert isinstance(result, Transaction)
        assert result.id == txn.id
        assert result.merchant_id == merchant.merchant_id
        assert result.status == TxnStatus.COMPLETED
        assert result.amount == amount
        assert result.net_amount == net_amount
        assert result.fee == fee