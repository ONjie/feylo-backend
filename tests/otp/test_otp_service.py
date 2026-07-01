import pytest
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from tests.conftest import db_session
from src.otp.otp_service import (
    get_otp, 
    save_otp, 
    generate_secure_otp, 
    verify_otp, 
    update_otp_attempts, 
    delete_otp, 
    send_otp_simulator
    )
from src.otp.exceptions import OTPNotFoundError, ExpiredOTPError, InvalidOTPError
from src.otp.models import OTP
from src.otp.schemas import OTPCreate, OTPSentResponse
from src.utils.config import settings
from sqlalchemy import select
from unittest.mock import patch


@pytest.mark.asyncio
class TestOTPService:

    @pytest.mark.parametrize(
        'phone_number, expected_exception, expected_message',
        [
            pytest.param(
                "+2202222456",
                None,
                None,
                id='get_otp_success'
            ),
            pytest.param(
                "+2202222498",
                OTPNotFoundError,
                "No active OTP session found for phone number: +2202222498.",
                id='get_otp_error'
            ),
        ]
    )
    async def test_get_otp(
        self, db_session, phone_number, expected_exception, expected_message):

        new_otp = OTP(
            phone_number="+2202222456",
            otp_hash="otp_hash",
            expiry_time=datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)
        )

        db_session.add(new_otp)
        await db_session.commit()


        if expected_exception:
            with pytest.raises(expected_exception) as exc:
                await get_otp(phone_number=phone_number, session=db_session)

            assert expected_message in str(exc.value)

        else:
            result = await get_otp(phone_number=phone_number, session=db_session)

            assert isinstance(result, OTP)
            assert result.phone_number == phone_number
            assert result.id is not None


    @pytest.mark.parametrize(
        "pre_seed_count",
        [
            pytest.param(0, id="save_initial_otp"),
            pytest.param(2, id="clear_existing_otps_and_save_new"),
        ],
    )
    async def test_save_otp(self, db_session, pre_seed_count):
        
        target_phone = "+2202234567"
        future_expiry = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)
        
        
        for i in range(pre_seed_count):
            stale_otp = OTP(
                phone_number=target_phone,
                otp_hash=f"stale_hash_{i}",
                expiry_time=datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)
            )
            db_session.add(stale_otp)
        
        if pre_seed_count > 0:
            await db_session.commit()
       
        new_otp = OTPCreate(
            phone_number=target_phone,
            hashed_otp="hashed_otp",
            raw_otp=123456,
            expiry_time=future_expiry
        )
       
        await save_otp(otp=new_otp, session=db_session)
       
        result = await db_session.execute(
            select(OTP).where(OTP.phone_number == target_phone)
        )
        current_records = result.scalars().all()
 
        assert len(current_records) == 1
        saved_record = current_records[0]
        assert saved_record.otp_hash == "hashed_otp"
        assert saved_record.expiry_time == future_expiry


    @pytest.mark.parametrize(
        'phone_number, otp_hashed',
        [
            pytest.param(
                "+2202225678",
                "hashed_otp",
                id="delete_otp_success"
            )
        ]
    )
    async def test_delete_otp(self, db_session, phone_number, otp_hashed):
        active_otp = OTP(
            phone_number=phone_number,
            otp_hash=otp_hashed,
            expiry_time=datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)
        )

        db_session.add(active_otp)
        await db_session.commit()
        await db_session.refresh(active_otp)


        result = await delete_otp(active_otp=active_otp, session=db_session)

        assert result == "OTP deleted successfully"

        db_check = await db_session.execute(
            select(OTP).where(OTP.phone_number == phone_number)
        )
        remaining_records = db_check.scalars().all()
        
        assert len(remaining_records) == 0


    @pytest.mark.parametrize(
        'phone_number, initial_attempt, expected_attempts',
        [
            pytest.param(
                "+2202233445", 0, 1, id='increment_from_zero'
            ),
            pytest.param(
                "+2202233447", 2, 3, id='increment_existing_otp_attempts'
            ),
        ]
    )
    async def test_update_otp_attempts(
        self, db_session,phone_number, initial_attempt, expected_attempts):
        active_otp = OTP(
            phone_number=phone_number,
            otp_hash="otp_hashed",
            expiry_time=datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS),
            otp_attempts=initial_attempt
        )

        db_session.add(active_otp)
        await db_session.commit()
        await db_session.refresh(active_otp)


        result = await update_otp_attempts(active_otp=active_otp, session=db_session)

        assert result == "Number of OTP attempts updated successfully"
        assert active_otp.otp_attempts == expected_attempts

        db_check = await db_session.execute(
            select(OTP).where(OTP.phone_number == phone_number)
        )
        persisted_record = db_check.scalar_one()
        assert persisted_record.otp_attempts == expected_attempts


    @pytest.mark.parametrize(
        "phone_number",
        [
            pytest.param("+2207000001", id="standard_gambia_phone"),
        ],
    )
    def test_generate_secure_otp_(self, phone_number):
    
        result = generate_secure_otp(phone_number=phone_number)

        assert isinstance(result, OTPCreate)
        assert result.phone_number == phone_number

        assert result.raw_otp.is_integer() is True


        assert result.expiry_time.tzinfo == timezone.utc
        assert result.expiry_time > datetime.now(timezone.utc)


    @pytest.mark.parametrize(
        'initial_state, submitted_otp, expected_exception, expected_message, expect_deleted',
        [
            pytest.param(
                {"attempts": 0, "minutes_offset": 5, "raw_secret": "123456"},
                "123456",
                None,
                None,
                True,
                id="verify_otp_success"
            ),
            pytest.param(
                {"attempts": 3, "minutes_offset": 5, "raw_secret": "123456"},
                "123456",
                InvalidOTPError,
                "Too many failed attempts. Please request a new verification code.",
                True,
                id="brute_force_lockout"
            ),
            pytest.param(
                {"attempts": 0, "minutes_offset": -5, "raw_secret": "123456"},
                "123456",
                ExpiredOTPError,
                "The verification code has expired.",
                True,
                id="code_expired"
            ),
            pytest.param(
                {"attempts": 0, "minutes_offset": 5, "raw_secret": "123456"},
                "999999",
                InvalidOTPError,
                "Invalid verification code.",
                False, 
                id="wrong_code_increments_attempts"
            ),
        ],
    )
    async def test_verify_otp(
        self, db_session, initial_state, submitted_otp, expected_exception, expected_message, expect_deleted
        ):
        phone_number = "+2202224567"  
        hashed_secret = hashlib.sha256(initial_state["raw_secret"].encode("utf-8")).hexdigest()
        expiry = datetime.now(timezone.utc) + timedelta(minutes=initial_state["minutes_offset"])

        active_otp = OTP(
            phone_number=phone_number,
            otp_hash=hashed_secret,
            expiry_time=expiry,
            otp_attempts=initial_state["attempts"]
        )
        db_session.add(active_otp)
        await db_session.commit()

        
        if expected_exception:
            with pytest.raises(expected_exception) as exc_info:
                await verify_otp(phone_number=phone_number, submitted_otp=submitted_otp, session=db_session)
            
            assert expected_message in str(exc_info.value)
            
            
            if not expect_deleted:
                await db_session.refresh(active_otp)
                assert active_otp.otp_attempts == initial_state["attempts"] + 1
        else:
            result = await verify_otp(phone_number=phone_number, submitted_otp=submitted_otp, session=db_session)
            assert result is True

        
        from sqlalchemy import select
        db_check = await db_session.execute(select(OTP).where(OTP.phone_number == phone_number))
        remaining_record = db_check.scalar_one_or_none()
        
        if expect_deleted:
            assert remaining_record is None, "Expected OTP token to be purged from the database."
        else:
            assert remaining_record is not None, "Expected OTP token to remain active in the database."


    @pytest.mark.parametrize(
        "is_login, expected_log_snippet",
        [
            pytest.param(
                True, 
                "Your Feylo Merchant Payment login code is:", 
                id="sms_flow_login_message"
            ),
            pytest.param(
                False, 
                "Welcome to Feylo Merchant Payment! Your verification code is:", 
                id="sms_flow_registration_message"
            ),
        ],
    )
    @patch("src.otp.otp_service.logger")  
    async def test_send_otp_simulator(
        self, mock_logger, db_session, is_login, expected_log_snippet
    ):
        phone_number = "+2202224567"

        result = await send_otp_simulator(phone_number=phone_number, is_login=is_login, session=db_session)

      
        assert isinstance(result, OTPSentResponse)
        assert result.message == "OTP sent — check your phone"

        db_check = await db_session.execute(
            select(OTP).where(OTP.phone_number == phone_number)
        )
        saved_otp_record = db_check.scalar_one_or_none()
        
        assert saved_otp_record is not None, "Expected OTP token to be committed into the database."
        assert len(saved_otp_record.otp_hash) == 64  

        called_message_log = mock_logger.info.call_args_list[2][0][0]
        
        assert expected_log_snippet in called_message_log
        assert phone_number not in called_message_log