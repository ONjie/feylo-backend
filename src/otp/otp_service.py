import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.utils.config import settings
from src.otp.schemas import OTPCreate, OTPSentResponse
from src.otp.models import OTP
from src.otp.exceptions import (
    OTPNotFoundError, 
    InvalidOTPError, 
    ExpiredOTPError
    )

import logging
import sys

logging.basicConfig(
    level=logging.INFO,                                
    format="%(asctime)s [%(levelname)s] %(message)s",  
    handlers=[logging.StreamHandler(sys.stdout)]  
)
logger = logging.getLogger(__name__)


async def get_otp(phone_number: str, session: AsyncSession) -> OTP:
    result = await session.execute(
        select(OTP).where(OTP.phone_number == phone_number))
    
    existing_otp = result.scalar_one_or_none()

    if not existing_otp:
        raise OTPNotFoundError(f"No active OTP session found for phone number: {phone_number}.")
    return existing_otp


async def save_otp(otp: OTPCreate, session: AsyncSession) -> None:
    existing_otps = await session.execute(
        select(OTP).where(OTP.phone_number == otp.phone_number)
    )
    for row in existing_otps.scalars().all():
        await session.delete(row)
        
    new_db_otp = OTP(
        phone_number=otp.phone_number,
        otp_hash=otp.hashed_otp,
        expiry_time=otp.expiry_time
    )
    session.add(new_db_otp)
    await session.commit()


async def delete_otp(active_otp: OTP, session: AsyncSession) -> str:
    await session.delete(active_otp)
    await session.commit()
    return 'OTP deleted successfully'


async def update_otp_attempts(active_otp: OTP, session: AsyncSession) -> str:
    active_otp.otp_attempts +=1
    await session.commit()
    await session.refresh(active_otp)
    return 'Number of OTP attempts updated successfully'


def generate_secure_otp(phone_number: str) -> OTPCreate:
    raw_otp = f"{secrets.randbelow(1_000_000):06d}"
    expiry_time = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)
    hashed_otp = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()
    
    return OTPCreate(
        phone_number=phone_number,
        raw_otp=int(raw_otp),
        hashed_otp=hashed_otp,
        expiry_time=expiry_time
    )


async def verify_otp(phone_number: str, submitted_otp: str, session: AsyncSession) -> bool:

    active_otp = await get_otp(phone_number=phone_number, session=session)

    if active_otp.otp_attempts >= 3:
        await delete_otp(active_otp=active_otp, session=session)
        raise InvalidOTPError("Too many failed attempts. Please request a new verification code.")
    
    otp_expiry_time = active_otp.expiry_time.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > otp_expiry_time:
        await delete_otp(active_otp=active_otp, session=session)
        raise ExpiredOTPError("The verification code has expired.")
    
    hashed_submitted_otp = hashlib.sha256(submitted_otp.encode("utf-8")).hexdigest()

    if not secrets.compare_digest(active_otp.otp_hash, hashed_submitted_otp):
        await update_otp_attempts(active_otp=active_otp, session=session)
        raise InvalidOTPError("Invalid verification code.")
    
    await delete_otp(active_otp=active_otp, session=session)
    return True


async def send_otp_simulator(
        phone_number: str, 
        is_login: bool,
        session: AsyncSession
        ) -> str:

    generated_otp = generate_secure_otp(phone_number=phone_number)
    await save_otp(otp=generated_otp, session=session)

    if is_login: 
        message = f"Your Feylo Merchant Payment login code is: {generated_otp.raw_otp}. Valid for 10 minutes. Do not share."
    else:
        message=( 
                f"Welcome to Feylo Merchant Payment! Your verification code is: {generated_otp.raw_otp}."
                f"Valid for 10 minutes. Do not share."
                )

    logger.info("=" * 60)
    logger.info(f"[SMS SIMULATOR] To: {phone_number}")
    logger.info(f"[SMS SIMULATOR] Message: {message}")
    logger.info("=" * 60)

    return OTPSentResponse(message="OTP sent — check your phone")



