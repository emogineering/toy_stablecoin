from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
import logging

# KST 타임존 설정
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 시간을 KST로 반환"""
    return datetime.now(KST)

# 로깅 설정
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./toy_stable.db')

# 데이터베이스 엔진 설정 (연결 풀 포함)
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # 연결 풀 크기
    max_overflow=20,  # 최대 오버플로우 연결 수
    pool_pre_ping=True,  # 연결 전 핑 테스트
    pool_recycle=3600,  # 1시간마다 연결 재생성
    echo=False  # SQL 로깅 비활성화 (필요시 True로 변경)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MintRequest(Base):
    __tablename__ = "mint_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    eth_address = Column(String, index=True)
    amount = Column(Float)
    tx_id = Column(String, index=True)  # 입금 트랜잭션 ID 추가
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=get_kst_now)

class BurnRequest(Base):
    __tablename__ = "burn_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    tx_id = Column(String, index=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=get_kst_now)

class UpbitTransfer(Base):
    __tablename__ = "upbit_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    tx_id = Column(String, unique=True, index=True)
    type = Column(String)  # deposit, withdraw
    amount = Column(Float)
    currency = Column(String)
    status = Column(String)
    created_at = Column(DateTime)

class UpbitBalanceHistory(Base):
    __tablename__ = "upbit_balance_history"
    
    id = Column(Integer, primary_key=True, index=True)
    usdt_balance = Column(Float)
    change_amount = Column(Float)
    change_type = Column(String)  # initial, trade_mint, trade_burn
    created_at = Column(DateTime, default=get_kst_now)

class UpbitTradeSync(Base):
    __tablename__ = "upbit_trade_sync"
    id = Column(Integer, primary_key=True, index=True)
    last_trade_uuid = Column(String, index=True)
    last_checked_at = Column(DateTime, default=get_kst_now)

def get_db():
    """데이터베이스 세션을 안전하게 제공하는 함수"""
    db = SessionLocal()
    try:
        # 연결 상태 확인
        result = db.query(1).first()
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 연결 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """데이터베이스 초기화"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise

def check_db_connection():
    """데이터베이스 연결 상태 확인"""
    try:
        db = SessionLocal()
        # 간단한 쿼리로 연결 상태 확인
        result = db.query(1).first()
        db.close()
        logger.info("데이터베이스 연결 상태 정상")
        return True
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return False 