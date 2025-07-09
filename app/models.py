from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()

class MintRequest(Base):
    __tablename__ = "mint_requests"
    id = Column(Integer, primary_key=True)
    eth_address = Column(String)
    amount = Column(Float)
    status = Column(String)  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)  # 신청 시각 

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # 데모용 SQLite 사용
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 