from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from docusight.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    try:
        db = session()
        yield db
    finally:
        db.close()
