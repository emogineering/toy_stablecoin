import os
from dotenv import load_dotenv
from typing import Optional
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

# .env 파일 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

class Settings:
    """애플리케이션 설정 클래스"""
    
    # 데이터베이스 설정
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///./toy_stable.db')
    
    # 업비트 API 설정
    UPBIT_ACCESS_KEY: Optional[str] = os.getenv('UPBIT_ACCESS_KEY')
    UPBIT_SECRET_KEY: Optional[str] = os.getenv('UPBIT_SECRET_KEY')
    
    # 애플리케이션 설정
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # 보안 설정
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-here')
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "이더리움 토큰 민팅 시스템"
    
    # CORS 설정
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",  # React 개발 서버
        "http://localhost:8000",  # FastAPI 개발 서버
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    def validate_settings(self) -> bool:
        """필수 설정값 검증"""
        errors = []
        
        # 업비트 API 키 검증
        if not self.UPBIT_ACCESS_KEY:
            errors.append("UPBIT_ACCESS_KEY가 설정되지 않았습니다.")
        if not self.UPBIT_SECRET_KEY:
            errors.append("UPBIT_SECRET_KEY가 설정되지 않았습니다.")
        
        # 데이터베이스 URL 검증
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL이 설정되지 않았습니다.")
        
        # 시크릿 키 검증
        if self.SECRET_KEY == 'your-secret-key-here':
            logger.warning("기본 SECRET_KEY를 사용하고 있습니다. 프로덕션에서는 변경하세요.")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        logger.info("모든 필수 설정이 올바르게 구성되었습니다.")
        return True
    
    def get_database_url(self) -> str:
        """데이터베이스 URL 반환 (SQLite 연결 옵션 포함)"""
        if self.DATABASE_URL.startswith('sqlite'):
            return f"{self.DATABASE_URL}?check_same_thread=False"
        return self.DATABASE_URL
    
    def is_development(self) -> bool:
        """개발 환경 여부 확인"""
        return self.DEBUG
    
    def get_cors_origins(self) -> list:
        """CORS 허용 오리진 반환"""
        if self.is_development():
            return ["*"]  # 개발 환경에서는 모든 오리진 허용
        return self.BACKEND_CORS_ORIGINS

# 전역 설정 인스턴스
settings = Settings()

def validate_environment():
    """환경 변수 검증 및 초기화"""
    if not settings.validate_settings():
        raise ValueError("필수 환경 변수가 설정되지 않았습니다.")
    
    # 로깅 레벨 설정
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"애플리케이션 설정 로드 완료 - 환경: {'개발' if settings.is_development() else '프로덕션'}")
    return True 