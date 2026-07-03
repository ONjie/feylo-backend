import pytest
from sqlalchemy import select
from tests.conftest import db_session
from src.wallet.models import Wallet, WalletLedger
from src.wallet.wallet_service import (
    create_wallet, 
    get_wallet, 
    wallet_credit, 
    get_wallet_ledger
)
from src.merchant.models import Merchant
from src.wallet.exceptions import WalletAlreadyExistError, WalletNotFoundError
from src.transaction.models import Transaction
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
class TestWalletService:

    @pytest.mark.parametrize(
        'should_duplicate, expected_exception',
        [
            pytest.param(
                False,
                None,
                id='create_wallet_success'
            ),
            pytest.param(
                True,
                WalletAlreadyExistError,
                id='create_wallet_failure'
            )
        ]
            
    )
    async def test_create_wallet(
        self, db_session, should_duplicate, expected_exception):
        new_merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )
        db_session.add(new_merchant)
        await db_session.commit()
        await db_session.refresh(new_merchant)
        

        if not should_duplicate:
            await create_wallet(merchant_id=new_merchant.merchant_id, session=db_session)

            db_check = await db_session.execute(
                select(Wallet).where(Wallet.merchant_id==new_merchant.merchant_id)
            )

            remaining_record = db_check.scalar_one_or_none()

            assert remaining_record is not None
            assert remaining_record.merchant_id == new_merchant.merchant_id

        else:
            await create_wallet(merchant_id=new_merchant.merchant_id, session=db_session)

            with pytest.raises(expected_exception) as exc:
               await create_wallet(merchant_id=new_merchant.merchant_id, session=db_session)
                
            assert f'Wallet with merchant id: {new_merchant.merchant_id} already exists.' in str(exc.value)



    @pytest.mark.parametrize(
            'wallet_exists, expected_exception',
            [
                pytest.param(
                    True,
                    None,
                    id='get_wallet_success'
                ),
                pytest.param(
                    False,
                    WalletNotFoundError,
                    id='get_wallet_failure'
                )
            ]
    )
    async def test_get_wallet(self, db_session, wallet_exists, expected_exception):

        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )
        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)

        if wallet_exists:
            new_wallet = Wallet(merchant_id=merchant.merchant_id)

            db_session.add(new_wallet)
            await db_session.commit()
            await db_session.refresh(new_wallet)


        if not expected_exception:
            result = await get_wallet(merchant_id=merchant.merchant_id, session=db_session)

            assert isinstance(result, Wallet)
            assert result.merchant_id == merchant.merchant_id
            assert result.id is not None
            

        else:
            with pytest.raises(expected_exception) as exc:
                await get_wallet(merchant_id=merchant.merchant_id, session=db_session)

            assert f"No wallet found for merchant id: {merchant.merchant_id}" in str(exc.value)



    @pytest.mark.parametrize(
        'wallet_exist, initial_balance, net_amount, expected_balance, expected_exception',
        [
            
            pytest.param(
                True, 100.00, 50.25, 150.25, None, 
                id="credit_success_adds_to_balance"
            ),
            pytest.param(
                True, 0.00, 99.99, 99.99, None, 
                id="credit_success_from_zero_balance"
            ),
            pytest.param(
                False, 0.00, 50.00, 0.00, WalletNotFoundError, 
                id="credit_failure_wallet_not_found"
            ),
            
        ]
    )
    async def test_wallet_credit(
        self, db_session, wallet_exist, initial_balance, net_amount, expected_balance, expected_exception):
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
            amount=51.50,
            fee=1.25,
            net_amount=net_amount,
            currency="GMD",
            provider="Wave"
            )

        wallet_id = None
        if wallet_exist:
            new_wallet = Wallet(merchant_id=merchant.merchant_id, balance=initial_balance)

            db_session.add(new_wallet)
            await db_session.commit()
            await db_session.refresh(new_wallet)
            wallet_id = new_wallet.id

        if not expected_exception:
            updated_wallet = await wallet_credit(txn=txn, session=db_session)


            assert float(updated_wallet.balance) == expected_balance

            
            ledger_query = await db_session.execute(
                select(WalletLedger).where(WalletLedger.transaction_id == txn.id)
            )
            ledger_entry = ledger_query.scalar_one_or_none()

            assert ledger_entry is not None
            assert ledger_entry.wallet_id == wallet_id
            assert ledger_entry.entry_type == "CREDIT"
            assert float(ledger_entry.amount) == net_amount
            assert float(ledger_entry.balance_after) == expected_balance
            
            
            expected_desc = "Payment received via Wave — GMD 51.50 (fee: 1.25)"
            assert ledger_entry.description == expected_desc

        else:
            with pytest.raises(expected_exception) as exc:
                await wallet_credit(txn=txn, session=db_session)

            assert f"No wallet found for merchant id: {merchant.merchant_id}" in str(exc.value)



    @pytest.mark.parametrize(
        "wallet_exist, total_ledger_records, query_limit, expected_count, expected_exception",
        [
            pytest.param(
                True, 5, 20, 5, None, 
                id="get_ledger_success_all_records_within_limit"
            ),
            pytest.param(
                True, 25, 10, 10, None, 
                id="get_ledger_success_respects_custom_limit"
            ),
            pytest.param(
                True, 0, 20, 0, None, 
                id="get_ledger_success_empty_ledger"
            ),
            pytest.param(
                False, 0, 20, 0, WalletNotFoundError, 
                id="get_ledger_failure_wallet_not_found"
            ),
        ],
    )
    async def test_get_wallet_ledger(
        self, db_session, wallet_exist, total_ledger_records, query_limit, expected_count, expected_exception
    ):
        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )
        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)

        if wallet_exist:
            new_wallet = Wallet(merchant_id=merchant.merchant_id, balance=100.00)
            db_session.add(new_wallet)
            await db_session.commit()
            await db_session.refresh(new_wallet)

            base_time = datetime.now(timezone.utc)
            for i in range(total_ledger_records):
                ledger_entry = WalletLedger(
                    wallet_id=new_wallet.id,
                    transaction_id=f"TXN_MOCK_{i}",
                    entry_type="CREDIT",
                    amount=10.00,
                    balance_after=10.00 * (i + 1),
                    description=f"Mock entry number {i}",
                    created_at=base_time + timedelta(minutes=i)
                )
                db_session.add(ledger_entry)
            
            await db_session.commit()
        
        
        if not expected_exception:
            
            ledgers = await get_wallet_ledger(
                session=db_session, 
                merchant_id=merchant.merchant_id, 
                limit=query_limit
            )

            assert len(ledgers) == expected_count

            if expected_count > 1:
                assert ledgers[0].created_at > ledgers[-1].created_at
                assert ledgers[0].transaction_id == f"TXN_MOCK_{total_ledger_records - 1}"

        else:
            with pytest.raises(expected_exception) as exc:
                await get_wallet_ledger(
                    session=db_session, 
                    merchant_id=merchant.merchant_id, 
                    limit=query_limit
                )

            assert f"No wallet found for merchant id: {merchant.merchant_id}" in str(exc.value)