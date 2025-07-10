import os
import jwt
import uuid
import requests
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

ACCESS_KEY = os.getenv('UPBIT_ACCESS_KEY')
SECRET_KEY = os.getenv('UPBIT_SECRET_KEY')
SERVER_URL = 'https://api.upbit.com'

def get_usdt_balance():
    if not ACCESS_KEY or not SECRET_KEY:
        raise Exception('API 키가 설정되어 있지 않습니다.')
    payload = {
        'access_key': ACCESS_KEY,
        'nonce': str(uuid.uuid4()),
    }
    jwt_token = jwt.encode(payload, SECRET_KEY)
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    res = requests.get(SERVER_URL + "/v1/accounts", headers=headers)
    res.raise_for_status()
    for item in res.json():
        if item['currency'] == 'USDT':
            return float(item['balance'])
    return 0.0

def get_transfers():
    if not ACCESS_KEY or not SECRET_KEY:
        raise Exception('API 키가 설정되어 있지 않습니다.')
    payload = {
        'access_key': ACCESS_KEY,
        'nonce': str(uuid.uuid4()),
    }
    jwt_token = jwt.encode(payload, SECRET_KEY)
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {"Authorization": authorize_token}

    # 입금 내역
    deposits = requests.get(
        SERVER_URL + "/v1/deposits",
        headers=headers,
        params={"currency": "USDT", "limit": 100}
    ).json()
    # 출금 내역
    withdraws = requests.get(
        SERVER_URL + "/v1/withdraws",
        headers=headers,
        params={"currency": "USDT", "limit": 100}
    ).json()
    # 결과 정리
    deposit_list = [
        {
            "tx_id": d["uuid"],
            "type": "deposit",
            "amount": float(d["amount"]),
            "currency": d["currency"],
            "status": d["state"],
            "created_at": d["created_at"]
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
            "created_at": w["created_at"]
        }
        for w in withdraws if isinstance(w, dict) and w.get("currency") == "USDT"
    ]
    return deposit_list + withdraw_list 