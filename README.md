# 이더리움 토큰 민팅 시스템

FastAPI 기반의 이더리움 토큰 민팅 신청 및 관리 시스템입니다. 업비트 API를 연동하여 USDT 잔액과 입출금 내역을 조회하고, 이를 바탕으로 자동 또는 수동으로 민팅 및 소각 신청을 생성하는 기능을 제공합니다.

## 🚀 주요 기능

### 백엔드 (FastAPI)
- **업비트 API 연동**: USDT 잔액 조회 및 입출금 내역 동기화
- **자동 민팅/소각 신청**: 잔액 변화 감지 시 자동 신청 생성
- **수동 관리**: 관리자용 수동 소각 신청 및 승인/거절 기능
- **실시간 통계**: 총 민팅량, 총 소각량, 현재 유통량, 계좌 잔액 표시
- **보안 강화**: 입력값 검증, 에러 핸들링, 로깅 시스템
- **환경 변수 관리**: 체계적인 설정 관리 및 검증

### 프론트엔드 (React)
- **관리자 페이지**: 입출금 내역, 민팅/소각 신청 목록, 통계 대시보드
- **사용자 페이지**: 민팅 신청 및 상태 확인
- **실시간 업데이트**: 자동 새로고침 및 상태 변경 알림

## 📋 시스템 요구사항

- Python 3.8+
- Node.js 16+
- 업비트 API 키 (Access Key, Secret Key)

## 🛠️ 설치 및 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd toy_stable
```

### 2. 백엔드 설정

#### 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

#### 의존성 설치
```bash
pip install -r requirements.txt
```

#### 환경 변수 설정 (.env 파일)
```env
# 업비트 API 설정
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here

# 데이터베이스 설정
DATABASE_URL=sqlite:///./toy_stable.db

# 애플리케이션 설정
DEBUG=True
LOG_LEVEL=INFO

# 보안 설정
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. 프론트엔드 설정

#### 의존성 설치
```bash
cd frontend
npm install
```

## 🚀 실행 방법

### 백엔드 서버 실행
```bash
# 가상환경 활성화 후
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프론트엔드 개발 서버 실행
```bash
cd frontend
npm start
```

### API 테스트
```bash
python test_api.py
```

## 📚 API 문서

서버 실행 후 다음 URL에서 Swagger UI를 통해 API 문서를 확인할 수 있습니다:
- http://localhost:8000/docs

## 🔧 주요 개선사항 (1순위 작업 완료)

### 1. 백엔드 안정성 강화
- **SQLAlchemy 쿼리 결과 타입 처리 개선**: None 값 안전 처리
- **데이터베이스 연결 풀 설정**: 연결 안정성 향상
- **세션 관리 개선**: 자동 롤백 및 연결 상태 확인

### 2. API 에러 핸들링 강화
- **업비트 API 호출 에러 처리**: 네트워크 오류, API 키 만료, 타임아웃 처리
- **데이터베이스 연결 실패 처리**: 재연결 로직 및 에러 복구
- **입력값 검증**: Pydantic 모델을 통한 데이터 유효성 검사

### 3. 입력값 검증 시스템
- **Pydantic 모델 도입**: 자동 데이터 검증 및 타입 안전성
- **사용자 입력 검증**: 금액 범위, 메모 길이 등 제한
- **API 응답 표준화**: 일관된 에러 메시지 및 상태 코드

### 4. 로깅 시스템 구축
- **체계적인 로깅**: 파일 및 콘솔 출력
- **요청/응답 로깅**: 미들웨어를 통한 API 호출 추적
- **에러 추적**: 상세한 에러 로그 및 디버깅 정보
- **성능 모니터링**: 요청 처리 시간 측정

### 5. 환경 변수 관리
- **설정 검증 시스템**: 필수 환경 변수 자동 검증
- **개발/프로덕션 환경 분리**: 환경별 설정 관리
- **보안 경고**: 기본값 사용 시 경고 메시지

### 6. 보안 강화
- **CORS 설정 개선**: 환경별 허용 오리진 관리
- **입력값 검증**: SQL 인젝션 및 XSS 공격 방지
- **에러 정보 노출 제한**: 민감한 정보 보호

## 📊 데이터베이스 스키마

### 주요 테이블
- `mint_requests`: 민팅 신청 내역
- `burn_requests`: 소각 신청 내역
- `upbit_transfers`: 업비트 입출금 내역
- `upbit_balance_history`: 잔액 변화 이력

## 🔄 향후 개발 계획

### 2순위: 실제 블록체인 연동
- 이더리움 네트워크 연동
- 스마트 컨트랙트 배포 및 관리
- 실제 토큰 민팅/소각 기능 구현

### 3순위: 사용자 경험 개선
- 실시간 알림 시스템
- 모바일 반응형 UI
- 다국어 지원

### 4순위: 고급 기능
- 다중 지갑 지원
- 거래 이력 분석
- 자동화된 리밸런싱

## 🐛 문제 해결

### 일반적인 문제들

1. **업비트 API 키 오류**
   - `.env` 파일의 API 키가 올바른지 확인
   - 업비트에서 API 키 권한 설정 확인

2. **데이터베이스 연결 오류**
   - SQLite 파일 권한 확인
   - 데이터베이스 파일 경로 확인

3. **포트 충돌**
   - 8000번 포트가 사용 중인지 확인
   - 다른 포트로 변경하여 실행

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 