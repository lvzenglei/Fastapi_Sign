from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# The file will be located at the same directory in the file fastapi.db
# SQLALCHEMY_DATABASE_URL = "sqlite:///./fastapi.db"
# If you were using a PostgreSQL database instead, you would just have to uncomment the line:
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/postgres"
# connect_args={"check_same_thread": False} ...is needed only for SQLite. It's not needed for other databases.
    # in FastAPI, using normal functions (def) more than one thread could interact with the database for the same request, so we need to make SQLite know that it should allow that with 
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()