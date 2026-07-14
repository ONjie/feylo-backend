from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.utils.config import settings
from src.utils.database import get_db_session, init_db_tables
from src.auth.auth_route import router as auth_router
from src.payment.payment_route import router as payment_router
from src.transaction.transaction_route import router as transaction_router
from src.merchant.merchant_route import router as merchant_router

async def lifespan(app: FastAPI):
    await init_db_tables()
    yield



app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

API_PREFIX = "/api/v1"

app.include_router(router=auth_router, prefix=API_PREFIX)
app.include_router(router=payment_router, prefix=API_PREFIX)
app.include_router(router=transaction_router, prefix=API_PREFIX)
app.include_router(router=merchant_router, prefix=API_PREFIX)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    db_status = "healthy" if result.scalar() == 1 else "unhealthy"
    
    return {
        "status": "online",
        "project": settings.APP_NAME,
        "database_connectivity": db_status
    }