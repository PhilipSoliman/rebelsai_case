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


async def drop_tables(**drop_table_flags):
    """
    Drop tables based on keyword arguments. Example usage:
    await drop_tables(users=True, documents=False)
    If a table's flag is True, it will be dropped. If no flags are provided, all tables are dropped.
    """
    async with engine.begin() as conn:
        if drop_table_flags:
            for table in Base.metadata.sorted_tables:
                flag = drop_table_flags.get(table.name, False)
                if flag:
                    await conn.run_sync(table.drop)
        else:
            # Drop all tables if no flags are provided
            for table in Base.metadata.sorted_tables:
                await conn.run_sync(table.drop)
