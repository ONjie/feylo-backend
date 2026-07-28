from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.utils.config import settings
from src.utils.database import get_db_session, init_db_tables
from src.auth.auth_routes import router as auth_router
from src.payment.payment_routes import router as payment_router
from src.transaction.transaction_routes import router as transaction_router
from src.merchant.merchant_routes import router as merchant_router
from src.websocket.websocket_routes import router as websocket_router
from src.payment.payment_webhook_routes import router as payment_webhook_router
from src.checkout.checkout_routes import router as checkout_router
from src.websocket.websocket_manager import manager

from fastapi.middleware.cors import CORSMiddleware

async def lifespan(app: FastAPI):
    await init_db_tables()
    await manager.start_listening()
    yield
    await manager.stop_listening()



app = FastAPI(
    title=settings.APP_NAME, 
    description="Unified Merchant Payment Gateway for The Gambia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(router=auth_router, prefix=API_PREFIX)
app.include_router(router=payment_router, prefix=API_PREFIX)
app.include_router(router=transaction_router, prefix=API_PREFIX)
app.include_router(router=merchant_router, prefix=API_PREFIX)
app.include_router(router=payment_webhook_router, prefix=API_PREFIX)
app.include_router(router=checkout_router, prefix=API_PREFIX)

app.include_router(router=websocket_router)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    db_status = "healthy" if result.scalar() == 1 else "unhealthy"
    
    return {
        "status": "online",
        "project": settings.APP_NAME,
        "database_connectivity": db_status
    }