import os
import jwt
import uuid
import requests
from dotenv import load_dotenv
import logging
import hashlib
import urllib.parse
import time
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

ACCESS_KEY = os.getenv('UPBIT_ACCESS_KEY')
SECRET_KEY = os.getenv('UPBIT_SECRET_KEY')
SERVER_URL = 'https://api.upbit.com'

def parse_datetime(dt_str):
    try:
        # ISO8601 + 타임존 문자열 처리
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None

def get_usdt_balance():
    if not ACCESS_KEY or not SECRET_KEY:
        raise Exception('API 키가 설정되어 있지 않습니다.')
    
    try:
        payload = {
            'access_key': ACCESS_KEY,
            'nonce': str(uuid.uuid4()),
        }
        jwt_token = jwt.encode(payload, SECRET_KEY)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        response = requests.get(SERVER_URL + "/v1/accounts", headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        for item in data:
            if item.get('currency') == 'USDT':
                balance = float(item.get('balance', 0))
                logger.info(f"USDT 잔액 조회 성공: {balance}")
                return balance
        
        logger.warning("USDT 잔액을 찾을 수 없습니다.")
        return 0.0
        
    except requests.exceptions.Timeout:
        logger.error("업비트 API 요청 시간 초과")
        raise Exception("업비트 API 요청 시간 초과")
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"업비트 API 응답: {e.response.text}")
        logger.error(f"업비트 API 요청 실패: {e}")
        raise Exception(f"업비트 API 요청 실패: {e}")
    except jwt.InvalidTokenError:
        logger.error("JWT 토큰 생성 실패")
        raise Exception("API 키가 유효하지 않습니다.")
    except Exception as e:
        logger.error(f"USDT 잔액 조회 중 예상치 못한 오류: {e}")
        raise Exception(f"잔액 조회 실패: {e}")

def get_transfers():
    if not ACCESS_KEY or not SECRET_KEY:
        raise Exception('API 키가 설정되어 있지 않습니다.')
    
    try:
        # 파라미터 순서 명확히 지정
        params = [("currency", "USDT"), ("limit", 100)]
        query_string = urllib.parse.urlencode(params)
        m = hashlib.sha512()
        m.update(query_string.encode())
        query_hash = m.hexdigest()
        logger.info(f"쿼리 문자열: {query_string}")
        logger.info(f"쿼리 해시: {query_hash}")

        # 입금 내역: 완전히 새로운 nonce, JWT, 헤더 생성
        nonce_deposit = str(uuid.uuid4())
        logger.info(f"deposit nonce length: {len(nonce_deposit)}, nonce: {nonce_deposit}")
        payload_deposit = {
            'access_key': ACCESS_KEY,
            'nonce': nonce_deposit,
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512'
        }
        jwt_token_deposit = jwt.encode(payload_deposit, SECRET_KEY, algorithm="HS256")
        headers_deposit = {"Authorization": f"Bearer {jwt_token_deposit}"}
        deposits_response = requests.get(
            SERVER_URL + "/v1/deposits",
            headers=headers_deposit,
            params=dict(params),
            timeout=10
        )
        deposits_response.raise_for_status()
        deposits = deposits_response.json()

        # 출금 내역: 완전히 새로운 nonce, JWT, 헤더 생성
        nonce_withdraw = str(uuid.uuid4())
        logger.info(f"withdraw nonce length: {len(nonce_withdraw)}, nonce: {nonce_withdraw}")
        payload_withdraw = {
            'access_key': ACCESS_KEY,
            'nonce': nonce_withdraw,
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512'
        }
        jwt_token_withdraw = jwt.encode(payload_withdraw, SECRET_KEY, algorithm="HS256")
        headers_withdraw = {"Authorization": f"Bearer {jwt_token_withdraw}"}
        withdraws_response = requests.get(
            SERVER_URL + "/v1/withdraws",
            headers=headers_withdraw,
            params=dict(params),
            timeout=10
        )
        withdraws_response.raise_for_status()
        withdraws = withdraws_response.json()
        
        # 결과 정리
        deposit_list = [
            {
                "tx_id": d["uuid"],
                "type": "deposit",
                "amount": float(d["amount"]),
                "currency": d["currency"],
                "status": d["state"],
                "created_at": parse_datetime(d["created_at"])
            }
            for d in deposits if isinstance(d, dict) and d.get("currency") == "USDT"
        ]
        withdraw_list = [
            {
                "tx_id": w["uuid"],
                "type": "withdraw",
                "amount": float(w["amount"]),
                "currency": w["currency"],
                "status": w["state"],
                "created_at": parse_datetime(w["created_at"])
            }
            for w in withdraws if isinstance(w, dict) and w.get("currency") == "USDT"
        ]
        logger.info(f"입금 내역: {deposit_list}")
        logger.info(f"출금 내역: {withdraw_list}")
        if not deposit_list:
            logger.warning("업비트 API에서 입금 내역이 비어 있습니다.")
        if not withdraw_list:
            logger.warning("업비트 API에서 출금 내역이 비어 있습니다.")
        for d in deposit_list:
            if d["amount"] <= 0:
                logger.warning(f"0 이하 금액의 입금 내역 감지: {d}")
        for w in withdraw_list:
            if w["amount"] <= 0:
                logger.warning(f"0 이하 금액의 출금 내역 감지: {w}")
        logger.info(f"입출금 내역 조회 성공: 입금 {len(deposit_list)}건, 출금 {len(withdraw_list)}건")
        return deposit_list + withdraw_list
        
    except requests.exceptions.Timeout:
        logger.error("업비트 API 요청 시간 초과")
        raise Exception("업비트 API 요청 시간 초과")
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"업비트 API 응답: {e.response.text}")
        logger.error(f"업비트 API 요청 실패: {e}")
        raise Exception(f"업비트 API 요청 실패: {e}")
    except jwt.InvalidTokenError:
        logger.error("JWT 토큰 생성 실패")
        raise Exception("API 키가 유효하지 않습니다.")
    except Exception as e:
        logger.error(f"입출금 내역 조회 중 예상치 못한 오류: {e}")
        raise Exception(f"입출금 내역 조회 실패: {e}") 

def get_usdt_trades():
    """USDT 마켓의 최근 체결(매수/매도) 내역을 조회한다."""
    if not ACCESS_KEY or not SECRET_KEY:
        raise Exception('API 키가 설정되어 있지 않습니다.')
    try:
        params = [
            ("market", "KRW-USDT"),
            ("state", "done"),
            ("order_by", "desc"),
            ("limit", 20)
        ]
        query_string = urllib.parse.urlencode(params)
        m = hashlib.sha512()
        m.update(query_string.encode())
        query_hash = m.hexdigest()
        payload = {
            'access_key': ACCESS_KEY,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
        jwt_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {jwt_token}"}
        url = f"{SERVER_URL}/v1/orders?{query_string}"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        orders = resp.json()
        # 주요 정보만 추출
        trades = []
        for o in orders:
            if o.get("market") == "KRW-USDT" and o.get("state") == "done":
                trades.append({
                    "uuid": o["uuid"],
                    "side": o["side"],  # bid(매수), ask(매도)
                    "price": float(o["price"]),
                    "volume": float(o["volume"]),
                    "created_at": parse_datetime(o["created_at"]),
                })
        return trades
    except Exception as e:
        logger.error(f"USDT 체결 내역 조회 실패: {e}")
        raise 