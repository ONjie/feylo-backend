import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import status
from tests.conftest import db_session
from src.transaction.models import Transaction
from src.transaction.schemas import TransactionRead
from datetime import datetime, timezone, timedelta
from src.merchant.models import Merchant
from src.utils.config import settings
from main import app
from src.utils.database import get_db_session
from src.auth.security import create_access_token


@pytest.mark.asyncio
class TestTransactionRoute:
    base_url = "http://test"

    @pytest.mark.parametrize(
        'transaction_id, wrong_merchant_id, transaction_exist, expected_http_status',
        [
            pytest.param(
                'TXN_1234', 
                None, 
                True, 
                status.HTTP_200_OK, 
                id='get_transaction_id_endpoint_success'
            ),
            pytest.param(
                'TXN_2234', 
                None,
                False, 
                status.HTTP_404_NOT_FOUND,  
                id='transaction_not_found_failure'
            ),
            pytest.param(
                'TXN_2468', 
                'MERCH_1234',
                True, 
                status.HTTP_403_FORBIDDEN,  
                id='not_your_transaction_failure'
            ),
        ]
    )
    async def test_get_transaction_id_endpoint(
        self, 
        db_session, 
        transaction_id, 
        wrong_merchant_id,
        transaction_exist, 
        expected_http_status
        ):

        app.dependency_overrides[get_db_session] = lambda: db_session

        merchant = Merchant(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
            is_verified=True,
            is_active=True
            )
        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)


        if wrong_merchant_id is not None:
            wrong_merchant = Merchant(
            merchant_id=wrong_merchant_id,
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
            is_verified=True,
            is_active=True
            )

            db_session.add(wrong_merchant)
            await db_session.commit()
            await db_session.refresh(wrong_merchant)


        if transaction_exist:
            txn = Transaction(
                id=transaction_id,
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

        merchant_id = wrong_merchant.merchant_id if wrong_merchant_id is not None else merchant.merchant_id

        token_string = create_access_token(merchant_id=merchant_id)

        headers = {"Authorization": f"Bearer {token_string}"}

        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.get(f'/api/v1/transactions/{transaction_id}', headers=headers)

        app.dependency_overrides.clear()

        print(f'json: {response.json()}')

        assert response.status_code == expected_http_status
        json_data = response.json()

        if response.status_code == status.HTTP_200_OK:
            assert json_data['id'] == txn.id
            assert json_data['merchant_id'] == merchant.merchant_id
            assert json_data['amount'] == txn.amount
        
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            assert json_data['detail'] == f"Transaction {transaction_id} not found"

        elif response.status_code == status.HTTP_403_FORBIDDEN:
            assert json_data['detail'] == "Not your transaction"

        


    @pytest.mark.parametrize(
        "has_transactions, expected_http_status",
        [
            pytest.param(True, status.HTTP_200_OK, id="get_transactions_list_endpoint_success"),
            pytest.param(False, status.HTTP_404_NOT_FOUND, id="get_transactions_list_endpoint_failure"),
        ]
    )
    async def test_get_transactions_list_endpoint(
        self, 
        db_session, 
        has_transactions, 
        expected_http_status
    ):
        app.dependency_overrides[get_db_session] = lambda: db_session

        merchant = Merchant(
            merchant_id="MERCH_1234",
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
            is_verified=True,
            is_active=True
        )
        db_session.add(merchant)
        await db_session.commit()
        await db_session.refresh(merchant)

        
        if has_transactions:
            for i in range(3):
                txn = Transaction(
                    id=f"TXN_123{i}",
                    merchant_id=merchant.merchant_id,
                    amount=50.00 * (i + 1),
                    fee=0.50,
                    net_amount=(49.50 * (i + 1)) - 1.00,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(minutes=settings.QR_EXPIRY_MINUTES),
                )
                db_session.add(txn)
                await db_session.commit()
                await db_session.refresh(txn)

        
        token_string = create_access_token(merchant_id=merchant.merchant_id)
        headers = {"Authorization": f"Bearer {token_string}"}
        payload = {
            "page":1,
            "per_page":10
        }
    
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=self.base_url) as client:
            response = await client.get('/api/v1/transactions?page=1&per_page=10', headers=headers)
 
        app.dependency_overrides.clear()


        assert response.status_code == expected_http_status
        json_data = response.json()

        if response.status_code == status.HTTP_200_OK:
            assert json_data["total"] == 3
            assert len(json_data["transactions"]) == 3
            assert json_data["transactions"][0]["id"] == "TXN_1232" 
        
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            assert json_data["detail"] == f"No transactions found for merchant {merchant.merchant_id}"


        

        
            

        
