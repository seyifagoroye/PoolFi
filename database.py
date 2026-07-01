import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the synchronous engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for data models
Base = declarative_base()

def get_db():
    """Dependency injection to manage database lifecycle per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()