from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.user import router as user_router
from app.admin import router as admin_router
from app.config import settings, validate_environment
from app.models import init_db, check_db_connection
import logging
import time
from datetime import datetime

# 환경 변수 검증
try:
    validate_environment()
except ValueError as e:
    print(f"환경 변수 검증 실패: {e}")
    exit(1)

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    debug=settings.is_development()
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 요청 로깅
    logger.info(f"요청 시작: {request.method} {request.url.path} - {datetime.now()}")
    
    try:
        response = await call_next(request)
        
        # 응답 로깅
        process_time = time.time() - start_time
        logger.info(f"요청 완료: {request.method} {request.url.path} - 상태코드: {response.status_code} - 처리시간: {process_time:.3f}초")
        
        return response
    except Exception as e:
        # 에러 로깅
        process_time = time.time() - start_time
        logger.error(f"요청 실패: {request.method} {request.url.path} - 에러: {str(e)} - 처리시간: {process_time:.3f}초")
        raise

@app.on_event("startup")
async def startup_event():
    logger.info("애플리케이션 시작")
    
    # 데이터베이스 초기화
    try:
        init_db()
        if check_db_connection():
            logger.info("데이터베이스 연결 성공")
        else:
            logger.error("데이터베이스 연결 실패")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("애플리케이션 종료")

# 라우터 등록
app.include_router(user_router, prefix="/user")
app.include_router(admin_router, prefix="/admin")

@app.get("/")
def read_root():
    logger.info("루트 경로 접근")
    return {"message": "이더리움 토큰 민팅 시스템 API"}

@app.get("/health")
def health_check():
    logger.info("헬스 체크 요청")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()} 