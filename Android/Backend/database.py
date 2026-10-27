import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = None
if DATABASE_URL and "postgresql" in DATABASE_URL:
    try:
        pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine = pg_engine
        print("Connected to PostgreSQL Database")
    except Exception as e:
        print(f"PostgreSQL connection offline ({e}), falling back to local SQLite database")
        engine = None

if engine is None:
    engine = create_engine("sqlite:///./errno.db", connect_args={"check_same_thread": False})
    print("Connected to SQLite Local Database (errno.db)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
