import pytest
from src.merchant.merchant_service import (
    create_merchant, 
    get_merchant, 
    deactivate_merchant_account,
    update_merchant_is_verified_status
    )
from src.merchant.exceptions import (
    MerchantAlreadyExistError, 
    InvalidMerchantLookupError,
    MerchantNotFoundError
    )
from src.merchant.schemas import MerchantCreate, MerchantRead
from tests.conftest import db_session
from  src.merchant.models import Merchant
from src.transaction.models import Transaction
from src.wallet.models import Wallet

@pytest.mark.asyncio
class TestMerchantService:

    @pytest.mark.parametrize(
        'should_duplicate, expected_exception, expected_message', [
            pytest.param(
                False,
                None,
                None,
                id="create_merchant_success"
            ),
            pytest.param(
                True,
                MerchantAlreadyExistError,
                "Merchant account with phone number +2202234567 already exists.",
                id="create_merchant_failure"
            )
        ])
    async def test_create_merchant(
        self, db_session, should_duplicate, expected_exception, expected_message):
        merchant = MerchantCreate(
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",
        )

        if not should_duplicate:
            result = await create_merchant(merchant=merchant, session=db_session)
            
            assert result.first_name == "Muhammed"
            assert result.last_name == "Njie"
            assert result.business_name == "Njie Store"
            assert result.phone_number == "+2202234567"
            assert result.merchant_id is not None
        
        else:
            await create_merchant(merchant=merchant, session=db_session)

            await db_session.flush()

            with pytest.raises(expected_exception) as exc:
                await create_merchant(merchant=merchant, session=db_session)

            assert expected_message in str(exc.value)

    
    @pytest.mark.parametrize(
            'lookup_kwargs',
            [
                pytest.param(
                    {"merchant_id": "merchant_1234"}, id="by_merchant_id"
                ),
                pytest.param(
                    {"phone_number": "+2202234567"}, id="by_phone_number"
                )
            ]
    )
    async def test_get_merchant_success(self, db_session, lookup_kwargs):
        new_merchant = Merchant(
            merchant_id='merchant_1234',
            first_name="Muhammed",
            last_name="Njie",
            business_name="Njie Store",
            phone_number="+2202234567",   
        )

        db_session.add(new_merchant)
        await db_session.commit()

        result = await get_merchant(session=db_session, **lookup_kwargs)

        assert isinstance(result, MerchantRead)
        assert result.merchant_id == "merchant_1234"
        assert result.first_name == "Muhammed"
        assert result.last_name == "Njie"
        assert result.business_name == "Njie Store"
        assert result.phone_number == "+2202234567"


    @pytest.mark.parametrize(
            'look_kwargs, expected_exception, expected_message',
            [
                pytest.param(
                    {},
                    InvalidMerchantLookupError,
                    "Either merchant_id or phone_number must be provided.",
                    id="no_phone_number_and_merchant_id"
                ),
                pytest.param(
                    {"merchant_id": "merchant_1111"},
                    MerchantNotFoundError,
                    "Merchant merchant_1111 not found.",
                    id="not_found_by_merchant_id"
                ),
                pytest.param(
                    {"phone_number": "+2202222276"},
                    MerchantNotFoundError,
                    "Merchant +2202222276 not found.",
                    id="not_found_by_phone_number"
                ),
            ]
    )
    async def tests_get_merchant_error(
        self, db_session, look_kwargs, expected_exception, expected_message):
        with pytest.raises(expected_exception) as exc:
            await get_merchant(session=db_session, **look_kwargs)

        assert expected_message in str(exc.value)


    @pytest.mark.parametrize(
        'merchant_id, should_seed, expected_exception, expected_message',
        [
            pytest.param(
                'merchant_1234',
                True,
                None,
                None,
                id='deactivated_merchant_account_success'
            ),
            pytest.param(
                'merchant_1111',
                False,
                MerchantNotFoundError,
                'Merchant merchant_1111 not found',
                id='merchant_not_found'
            ),

        ]
    )
    async def test_deactivate_merchant_account(
        self, db_session, should_seed, merchant_id, expected_exception, expected_message):

        if should_seed:
            new_merchant = Merchant(
                merchant_id="merchant_1234",
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number="+2202234567",
                is_active=True,
            )
            db_session.add(new_merchant)
            await db_session.commit()

        if expected_exception:
            with pytest.raises(expected_exception) as exc:
                await deactivate_merchant_account(merchant_id=merchant_id, session=db_session)

            assert expected_message in str(exc.value)

        else:
            result = await deactivate_merchant_account(merchant_id=merchant_id, session=db_session)

            assert isinstance(result, MerchantRead)
            assert result.merchant_id == "merchant_1234"
            assert result.is_active == False

    
    @pytest.mark.parametrize(
        'merchant_id, should_seed, expected_exception, expected_message',
        [
            pytest.param(
                'merchant_1234',
                True,
                None,
                None,
                id='update_merchant_is_verified_status_success'
            ),
            pytest.param(
                'merchant_1111',
                False,
                MerchantNotFoundError,
                'Merchant merchant_1111 not found',
                id='merchant_not_found'
            ),

        ]
    )
    async def test_update_merchant_is_verified_status(
        self, db_session, should_seed, merchant_id, expected_exception, expected_message):

        if should_seed:
            new_merchant = Merchant(
                merchant_id="merchant_1234",
                first_name="Muhammed",
                last_name="Njie",
                business_name="Njie Store",
                phone_number="+2202234567",
                is_verified=True,
            )
            db_session.add(new_merchant)
            await db_session.commit()

        if expected_exception:
            with pytest.raises(expected_exception) as exc:
                await update_merchant_is_verified_status(merchant_id=merchant_id, session=db_session)

            assert expected_message in str(exc.value)

        else:
            result = await update_merchant_is_verified_status(merchant_id=merchant_id, session=db_session)

            assert isinstance(result, MerchantRead)
            assert result.merchant_id == "merchant_1234"
            assert result.is_verified == True

