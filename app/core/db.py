from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings


engine = create_engine(get_settings().database_url)
sessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def get_db():
    try:
        db = sessionLocal()
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False