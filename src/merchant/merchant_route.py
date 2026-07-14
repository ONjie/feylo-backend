from fastapi import APIRouter, Depends
from src.merchant.schemas import MerchantRead
from src.auth.security import  get_current_merchant

router = APIRouter(prefix="/merchant", tags=["merchant"])


@router.get('/profile')
async def get_merchant_endpoint(merchant: MerchantRead = Depends(get_current_merchant)):
    return merchant