# 이더리움 토큰 민팅 시스템

FastAPI 기반의 이더리움 토큰 민팅 신청 및 관리 시스템입니다. 업비트 API를 연동하여 USDT 잔액과 입출금 내역을 조회하고, 이를 바탕으로 자동 또는 수동으로 민팅 및 소각 신청을 생성하는 기능을 제공합니다.

## 🚀 주요 기능

### 백엔드 (FastAPI)
- **업비트 API 연동**: USDT 잔액 조회 및 입출금 내역 동기화
- **자동 민팅/소각 신청**: 입출금 내역, 잔액 변화, 초기 동기화 시 자동 신청 생성
- **초기 동기화**: DB가 비어있고 업비트 계좌에 USDT가 있으면 자동으로 민팅 신청 생성
- **중복 방지**: 같은 트랜잭션(tx_id, amount)로 여러 번 신청 생성 불가
- **관리자 승인/거절**: 모든 민팅/소각 신청은 반드시 관리자의 승인/거절 후 처리
- **실시간 통계**: 총 민팅량, 총 소각량, 현재 유통량, 계좌 잔액 표시
- **보안 강화**: 입력값 검증, 에러 핸들링, 로깅 시스템
- **환경 변수 관리**: 체계적인 설정 관리 및 검증

### 프론트엔드 (React)
- **관리자 페이지**: 입출금 내역, 민팅/소각 신청 목록, 통계 대시보드
- **승인/거절 버튼**: status='pending'일 때만 노출, 승인/거절 후 상태만 표시
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

## 🔧 주요 개선사항 (2024년 7월 기준)

### 1. 백엔드 안정성 강화
- **SQLAlchemy 쿼리 결과 타입 처리 개선**: None 값 안전 처리
- **데이터베이스 연결 풀 설정**: 연결 안정성 향상
- **세션 관리 개선**: 자동 롤백 및 연결 상태 확인
- **마이그레이션**: 민팅 신청 테이블에 tx_id 컬럼 추가

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

### 7. 중복 방지 및 승인/거절 로직
- **tx_id 기반 중복 체크**: 같은 트랜잭션에 대해 여러 번 신청 생성 방지
- **status='pending'**: 모든 신청은 승인/거절 전까지 pending 상태 유지
- **관리자 승인/거절 후에만 상태 변경**
- **초기 동기화 민팅 신청**: DB가 비어있고 USDT 잔액이 있으면 자동 생성

## 📊 데이터베이스 스키마

### 주요 테이블
- `mint_requests`: 민팅 신청 내역 (tx_id 포함)
- `burn_requests`: 소각 신청 내역
- `upbit_transfers`: 업비트 입출금 내역
- `upbit_balance_history`: 잔액 변화 이력

## 🔄 앞으로 해야 할 작업

### 1. 프론트엔드 UX 개선
- 민팅/소각 신청 승인/거절 시 실시간 알림 및 피드백 강화
- 초기 동기화 민팅 신청에 대한 별도 안내/표시
- 입출금 내역, 신청 내역 필터/검색/정렬 기능 추가

### 2. 감사 로그 및 이력 관리
- 모든 승인/거절/신청/동기화 이벤트에 대한 감사 로그 기록
- 관리자/사용자별 이력 추적 기능

### 3. 테스트 자동화 및 배포
- 백엔드/프론트엔드 통합 테스트 코드 작성
- CI/CD 파이프라인 구축 및 자동 배포

### 4. 알림 시스템
- 민팅/소각 신청 발생, 승인/거절 시 이메일/슬랙/웹훅 등 알림 연동

### 5. 고급 기능 및 보안
- 관리자 권한 관리(2FA, 세션 만료 등)
- API Rate Limit, Abuse 방지
- 실시간 대시보드/통계 고도화

### 6. 실제 블록체인 연동
- 이더리움 네트워크 연동 및 스마트 컨트랙트 배포
- 실제 토큰 민팅/소각 트랜잭션 처리

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