from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from docusight.config import settings
from docusight.models import Base, User

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as db:
        yield db


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(drop_users: bool = False):
    async with engine.begin() as conn:
        if drop_users:
            await conn.run_sync(User.__table__.drop)
        else:
            for table in Base.metadata.sorted_tables:
                if table.name != User.__tablename__:
                    await conn.run_sync(table.drop)
