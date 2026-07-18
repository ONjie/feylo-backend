import pytest_asyncio, pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.utils.database import Base
from testcontainers.redis import RedisContainer
from src.utils.config import settings


@pytest_asyncio.fixture(scope="module")
async def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="module")
async def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


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


@pytest_asyncio.fixture(scope="function")
async def redis_client_url(redis_container):
    
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(redis_container.port)
    
    url = f"redis://{host}:{port}/0"
    print(f'url: {url}')
    yield url

