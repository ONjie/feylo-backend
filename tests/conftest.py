import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.utils.database import Base


@pytest_asyncio.fixture(scope="module")
async def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_container):
    async_url = postgres_container.get_connection_url(driver="asyncpg")
    
    engine = create_async_engine(async_url, echo=False)
    
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    
   
    async with async_session_factory() as session:
        yield session
    
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
