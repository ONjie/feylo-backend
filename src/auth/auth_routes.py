from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from src.utils.database import get_db_session
from src.auth.schemas import RegisterRequest, LoginRequest, AuthResponse
from src.merchant.schemas import MerchantCreate, MerchantRead
from src.merchant.exceptions import (
    MerchantNotFoundError, 
    MerchantAlreadyExistError, 
    InvalidMerchantLookupError,
    )
from src.merchant.merchant_service import (
    get_merchant, 
    create_merchant, 
    update_merchant_is_verified_status
    )
from src.otp.otp_service import send_otp_simulator, verify_otp
from src.otp.schemas import (
    OTPSentResponse, 
    OTPVerifyRequest, 
    ResendOTPRequest
    )
from src.auth.security import create_access_token, get_current_merchant
from src.otp.exceptions import (
    OTPNotFoundError, 
    InvalidOTPError, 
    ExpiredOTPError
    )

from src.wallet.wallet_service import create_wallet
from src.wallet.exceptions import WalletAlreadyExistError


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post('/register', status_code=201, response_model=OTPSentResponse)
async def register_endpoint(payload:RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> str:
    try:
        merchant = MerchantCreate.model_validate(payload.model_dump())
        registered_merchant = await create_merchant(merchant=merchant, session=session)

        await create_wallet(merchant_id=registered_merchant.merchant_id, session=session)

        return await send_otp_simulator(
            phone_number=registered_merchant.phone_number,
            is_login=False,
            session=session
            )

    except (MerchantAlreadyExistError, WalletAlreadyExistError) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{e.message} — use /auth/login instead",
        )
    
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.errors()[0]["msg"]
        )
    

@router.post('/login', response_model=OTPSentResponse)
async def login_endpoint(payload: LoginRequest, session: AsyncSession=Depends(get_db_session)):
    try:

        existing_merchant = await get_merchant(
            phone_number=payload.phone_number, 
            session=session
            )
        
        return await send_otp_simulator(
            phone_number=existing_merchant.phone_number,
            is_login=True,
            session=session
        )

    except (MerchantNotFoundError, InvalidMerchantLookupError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.errors()[0]["msg"]
        )
    

@router.post('/verify-otp', response_model=AuthResponse)
async def verify_otp_endpoint(
    payload: OTPVerifyRequest, 
    session: AsyncSession=Depends(get_db_session)):
    try:
        await verify_otp(
            phone_number=payload.phone_number, 
            submitted_otp=payload.submitted_otp,
            session=session
        )

        existing_merchant = await get_merchant(
            phone_number=payload.phone_number, 
            session=session
            )
        
        await update_merchant_is_verified_status(
            merchant_id=existing_merchant.merchant_id,
            session=session
        )
        
        access_token = create_access_token(merchant_id=existing_merchant.merchant_id)

        return AuthResponse(
            access_token=access_token,
            merchant_id=existing_merchant.merchant_id,    
        )


    except (
        InvalidOTPError, 
        ExpiredOTPError, 
        OTPNotFoundError,
        MerchantNotFoundError,
        InvalidMerchantLookupError
        ) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.errors()[0]["msg"]
        )
    

@router.post('/resend-otp', response_model=OTPSentResponse)
async def resend_otp_endpoint(payload: ResendOTPRequest, session: AsyncSession=Depends(get_db_session)):
    try:

        existing_merchant = await get_merchant(
            phone_number=payload.phone_number, 
            session=session
            )
        
        return await send_otp_simulator(
            phone_number=existing_merchant.phone_number,
            is_login=True,
            session=session
        )

    except (MerchantNotFoundError, InvalidMerchantLookupError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.errors()[0]["msg"]
        )


@router.get('/status')
async def check_auth_status_endpoint(merchant: MerchantRead = Depends(get_current_merchant)):
    return {"status": "authenticated"}