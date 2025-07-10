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

class UpbitTransfer(Base):
    __tablename__ = "upbit_transfers"
    id = Column(Integer, primary_key=True)
    tx_id = Column(String, unique=True, index=True)  # 업비트 트랜잭션 ID
    type = Column(String)  # deposit(입금), withdraw(출금)
    amount = Column(Float)
    currency = Column(String)  # USDT 등
    status = Column(String)  # 완료, 대기 등
    created_at = Column(DateTime, default=datetime.utcnow)

class BurnRequest(Base):
    __tablename__ = "burn_requests"
    id = Column(Integer, primary_key=True)
    amount = Column(Float)
    tx_id = Column(String)
    status = Column(String)  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

class UpbitBalanceHistory(Base):
    __tablename__ = "upbit_balance_history"
    id = Column(Integer, primary_key=True)
    usdt_balance = Column(Float)
    change_amount = Column(Float)  # 변화량 (양수: 증가, 음수: 감소)
    change_type = Column(String)  # deposit, withdraw, trade, manual
    created_at = Column(DateTime, default=datetime.utcnow)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # 데모용 SQLite 사용
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 