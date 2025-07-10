#!/usr/bin/env python3
"""
API 테스트 스크립트
"""

import requests
import json
import time
from datetime import datetime

# API 기본 URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """헬스 체크 테스트"""
    print("=== 헬스 체크 테스트 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"헬스 체크 실패: {e}")
        return False

def test_admin_endpoints():
    """관리자 엔드포인트 테스트"""
    print("\n=== 관리자 엔드포인트 테스트 ===")
    
    # 대시보드 통계 조회
    print("1. 대시보드 통계 조회")
    try:
        response = requests.get(f"{BASE_URL}/admin/dashboard-stats")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"USDT 잔액: {stats.get('usdt_balance', 'N/A')}")
            print(f"총 민팅량: {stats.get('total_usdg_minted', 'N/A')}")
            print(f"총 소각량: {stats.get('total_usdg_burned', 'N/A')}")
            print(f"유통량: {stats.get('circulating_usdg', 'N/A')}")
        else:
            print(f"응답: {response.text}")
    except Exception as e:
        print(f"대시보드 통계 조회 실패: {e}")
    
    # 민팅 신청 목록 조회
    print("\n2. 민팅 신청 목록 조회")
    try:
        response = requests.get(f"{BASE_URL}/admin/mint-requests")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            requests_list = response.json()
            print(f"민팅 신청 수: {len(requests_list)}")
        else:
            print(f"응답: {response.text}")
    except Exception as e:
        print(f"민팅 신청 목록 조회 실패: {e}")
    
    # 소각 신청 목록 조회
    print("\n3. 소각 신청 목록 조회")
    try:
        response = requests.get(f"{BASE_URL}/admin/burn-requests")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            burn_requests = response.json()
            print(f"소각 신청 수: {len(burn_requests)}")
        else:
            print(f"응답: {response.text}")
    except Exception as e:
        print(f"소각 신청 목록 조회 실패: {e}")
    
    # 업비트 전송 내역 조회
    print("\n4. 업비트 전송 내역 조회")
    try:
        response = requests.get(f"{BASE_URL}/admin/upbit-transfers")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            transfers = response.json()
            print(f"전송 내역 수: {len(transfers)}")
        else:
            print(f"응답: {response.text}")
    except Exception as e:
        print(f"업비트 전송 내역 조회 실패: {e}")

def test_manual_burn():
    """수동 소각 신청 테스트"""
    print("\n=== 수동 소각 신청 테스트 ===")
    
    # 유효한 소각 신청
    print("1. 유효한 소각 신청")
    try:
        data = {"amount": 100.0, "memo": "테스트 소각"}
        response = requests.post(f"{BASE_URL}/admin/manual-burn", json=data)
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"소각 신청 생성 성공: ID {result.get('id')}, 금액 {result.get('amount')}")
        else:
            print(f"응답: {response.text}")
    except Exception as e:
        print(f"수동 소각 신청 실패: {e}")
    
    # 잘못된 금액으로 소각 신청
    print("\n2. 잘못된 금액으로 소각 신청")
    try:
        data = {"amount": -50.0, "memo": "잘못된 금액"}
        response = requests.post(f"{BASE_URL}/admin/manual-burn", json=data)
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {response.text}")
    except Exception as e:
        print(f"잘못된 소각 신청 테스트 실패: {e}")

def test_balance_change():
    """잔액 변화 감지 테스트"""
    print("\n=== 잔액 변화 감지 테스트 ===")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/check-balance-change")
        print(f"상태 코드: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"결과: {result.get('message')}")
        else:
            print(f"응답: {response.text}")
    except Exception as e:
        print(f"잔액 변화 감지 실패: {e}")

def main():
    """메인 테스트 함수"""
    print("이더리움 토큰 민팅 시스템 API 테스트")
    print(f"테스트 시작 시간: {datetime.now()}")
    print("=" * 50)
    
    # 서버가 실행 중인지 확인
    if not test_health_check():
        print("서버가 실행되지 않았습니다. 먼저 서버를 시작하세요.")
        return
    
    # 각종 테스트 실행
    test_admin_endpoints()
    test_manual_burn()
    test_balance_change()
    
    print("\n" + "=" * 50)
    print("테스트 완료")

if __name__ == "__main__":
    main() 