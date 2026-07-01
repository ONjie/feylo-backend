from pwdlib import PasswordHash
from datetime import datetime,timezone, timedelta
from jose import jwt, JWTError
from src.utils.config import settings
from src.auth.exceptions import InvalidTokenError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from src.utils.database import get_db_session
from src.merchant.schemas import MerchantRead
from src.merchant.merchant_service import get_merchant
from fastapi import HTTPException, status
from src.merchant.exceptions import MerchantNotFoundError

password_hash = PasswordHash.recommended()

bearer = HTTPBearer()


def hash_pin_code(pin_code: str) -> str:
        """Converts raw text pin code  into an un-reversible cryptographic hash."""
        return password_hash.hash(pin_code)

def verify_pin_code(plain_pin_code: str, hashed_pin_code: str) -> bool:
        """Compares incoming plain text login string against the recorded hash."""
        return password_hash.verify(plain_pin_code, hashed_pin_code)

def create_access_token(merchant_id: str)-> str:
        payload = {
                'sub': merchant_id,
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> str:
        try:
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                merchant_id = payload.get("sub")
                if not merchant_id:
                        raise InvalidTokenError(message="Invalid token payload")
                return merchant_id
        except JWTError:
                raise InvalidTokenError(message="Could not validate credentials")

async def get_current_merchant(
        cred: HTTPAuthorizationCredentials=Depends(bearer),
        session: AsyncSession = Depends(get_db_session)
        ) -> MerchantRead:
        try:
                merchant_id = decode_access_token(cred.credentials)

                merchant = await get_merchant(merchant_id=merchant_id, session=session)

        except MerchantNotFoundError as e:
                raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=e.message
                ) 
        except InvalidTokenError as e:
                raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=e.message
                )
        if not merchant.is_verified:
                raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Merchant phone number is not verified"
                )
                
        if not merchant.is_active:
                raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Merchant account is deactivated"
                )
    
        return merchant







