from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.utils.config import settings
from src.utils.database import get_db_session, init_db_tables
from src.auth.auth_route import router as auth_router

async def lifespan(app: FastAPI):
    await init_db_tables()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.include_router(router=auth_router)

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    db_status = "healthy" if result.scalar() == 1 else "unhealthy"
    
    return {
        "status": "online",
        "project": settings.APP_NAME,
        "database_connectivity": db_status
    }