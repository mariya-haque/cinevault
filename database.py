import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Try PostgreSQL first, fallback to SQLite if PostgreSQL is not running or database doesn't exist
    pg_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/cinevault"
    try:
        temp_engine = create_engine(pg_url, pool_pre_ping=True)
        # Try connecting to test if PostgreSQL server is online and database exists
        with temp_engine.connect() as conn:
            pass
        DATABASE_URL = pg_url
        engine = temp_engine
        print("Connected to PostgreSQL database successfully!")
    except Exception:
        print("PostgreSQL connection failed. Falling back to local SQLite database (cinevault.db).")
        DATABASE_URL = "sqlite:///./cinevault.db"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# FastAPI dependency — ek DB session deta hai aur request khatam hone par close kar deta hai
def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()