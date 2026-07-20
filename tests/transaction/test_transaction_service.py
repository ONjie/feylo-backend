import pytest
from sqlalchemy import select
from tests.conftest import db_session
from src.transaction.transaction_service import (
    create_pending_transaction, 
    get_transaction_by_id,
    complete_transaction,
    failed_transaction,
    get_transactions_list,
    expired_transaction
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


    @pytest.mark.parametrize(
        'amount, fee, net_amount',
        [
            pytest.param(
                50.0,
                0.50,
                49.50,
                id="failed_transaction_success"
            )
        ]
    )
    async def test_failed_transaction(self, db_session, amount, fee, net_amount):
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

        result = await failed_transaction(txn=txn, session=db_session)

        assert isinstance(result, Transaction)
        assert result.id == txn.id
        assert result.merchant_id == merchant.merchant_id
        assert result.status == TxnStatus.FAILED
        assert result.amount == amount
        assert result.net_amount == net_amount
        assert result.fee == fee


    @pytest.mark.parametrize(
        'page, per_page, expected_count, total_in_db',
        [
            pytest.param(1, 2, 2, 5, id='get_all_transaction_list_success_one'),  
            pytest.param(2, 2, 2, 5, id='get_all_transaction_list_success_two'), 
            pytest.param(1, 10, 5, 0, id='get_all_transaction_list_failure'), 
        ]
    )
    async def test_get_all_transaction_list(
        self, db_session, page, per_page, expected_count, total_in_db):

        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )
        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)

        if total_in_db != 0:
    
            for i in range(total_in_db):
                txn = Transaction(
                    merchant_id=merchant.merchant_id,
                    amount=50.00,
                    fee=0.50,
                    net_amount=49.50,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(minutes=settings.QR_EXPIRY_MINUTES),
                )
                db_session.add(txn)
                await db_session.commit()
                await db_session.refresh(txn)
            
            transactions, total = await get_transactions_list(
                session=db_session, 
                merchant_id=merchant.merchant_id, 
                page=page, 
                per_page=per_page
                )
            
            assert total == total_in_db
            assert len(transactions) == expected_count

            if expected_count > 1:
                for i in range(len(transactions) - 1):
                    assert (
                        transactions[i].created_at
                        >= transactions[i + 1].created_at
                    )


        else:
            with pytest.raises(TransactionNotFoundError) as exc:
                await get_transactions_list(
                session=db_session, 
                merchant_id=merchant.merchant_id, 
                page=page, 
                per_page=per_page
                )

            assert f"No transactions found for merchant {merchant.merchant_id}" in str(exc.value)

    @pytest.mark.parametrize(
        'amount, fee, net_amount',
        [
            pytest.param(
                50.0,
                0.50,
                49.50,
                id="expired_transaction_success"
            )
        ]
    )
    async def test_failed_transaction(self, db_session, amount, fee, net_amount):
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

        result = await expired_transaction(txn=txn, session=db_session)

        assert isinstance(result, Transaction)
        assert result.id == txn.id
        assert result.merchant_id == merchant.merchant_id
        assert result.status == TxnStatus.EXPIRED
        assert result.amount == amount
        assert result.net_amount == net_amount
        assert result.fee == fee

