from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.models import MintRequest, UpbitTransfer, BurnRequest, get_db, UpbitBalanceHistory
from sqlalchemy import func
from app.upbit_api import get_usdt_balance
from app.upbit_api import get_transfers
from datetime import datetime
from pydantic import BaseModel, validator
from typing import Optional
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 입력값 검증을 위한 Pydantic 모델
class ManualBurnRequest(BaseModel):
    amount: float
    memo: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('소각량은 0보다 커야 합니다.')
        if v > 1000000:  # 최대 100만 USDT
            raise ValueError('소각량은 1,000,000 USDT를 초과할 수 없습니다.')
        return v
    
    @validator('memo')
    def validate_memo(cls, v):
        if v and len(v) > 200:
            raise ValueError('메모는 200자를 초과할 수 없습니다.')
        return v

def initial_sync_if_needed(db: Session):
    # 민팅/소각/입출금 내역이 모두 없는 경우에만 동작
    mint_exists = db.query(MintRequest).first()
    burn_exists = db.query(BurnRequest).first()
    transfer_exists = db.query(UpbitTransfer).first()
    if not mint_exists and not burn_exists and not transfer_exists:
        usdt_balance = get_usdt_balance()
        if usdt_balance > 0:
            # 이미 같은 금액의 초기 동기화 민팅 신청이 있으면 중복 생성 방지
            exists_init = db.query(MintRequest).filter(
                MintRequest.amount == usdt_balance,
                MintRequest.status == 'pending',
                MintRequest.tx_id == 'initial_sync'
            ).first()
            if not exists_init:
                db.add(MintRequest(
                    eth_address='',
                    amount=usdt_balance,
                    tx_id='initial_sync',
                    status='pending'
                ))
                db.commit()
                logger.info(f"초기 동기화 민팅 신청 자동 생성: {usdt_balance} USDT")

@router.on_event("startup")
def on_startup():
    # DB 세션 생성
    db = next(get_db())
    try:
        initial_sync_if_needed(db)
    finally:
        db.close()

@router.get("/mint-requests")
def get_requests(db: Session = Depends(get_db)):
    try:
        return db.query(MintRequest).order_by(MintRequest.created_at.desc()).all()
    except Exception as e:
        logger.error(f"민팅 신청 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="민팅 신청 목록 조회 중 오류가 발생했습니다.")

@router.get("/all-requests")
def get_all_requests(db: Session = Depends(get_db)):
    try:
        # 민팅 신청과 소각 신청을 모두 가져와서 통합
        mint_requests = db.query(MintRequest).all()
        burn_requests = db.query(BurnRequest).all()
        
        # 통합된 리스트 생성
        all_requests = []
        
        # 민팅 신청 추가
        for req in mint_requests:
            all_requests.append({
                "id": req.id,
                "type": "mint",  # 민팅 타입
                "amount": req.amount,
                "eth_address": req.eth_address,
                "tx_id": req.tx_id,
                "status": req.status,
                "created_at": req.created_at
            })
        
        # 소각 신청 추가
        for req in burn_requests:
            all_requests.append({
                "id": req.id,
                "type": "burn",  # 소각 타입
                "amount": req.amount,
                "eth_address": None,  # 소각은 주소가 없음
                "tx_id": req.tx_id,
                "status": req.status,
                "created_at": req.created_at
            })
        
        # 생성일시 기준으로 내림차순 정렬
        all_requests.sort(key=lambda x: x["created_at"], reverse=True)
        
        return all_requests
    except Exception as e:
        logger.error(f"통합 신청 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="신청 목록 조회 중 오류가 발생했습니다.")

@router.post("/approve/{request_id}")
def approve_request(request_id: int, db: Session = Depends(get_db)):
    if request_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 신청 ID입니다.")
    
    try:
        mint_req = db.query(MintRequest).filter(MintRequest.id == request_id).first()
        if not mint_req:
            raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
        if str(mint_req.status) != "pending":
            raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
        
        setattr(mint_req, 'status', 'approved')
        db.commit()
        db.refresh(mint_req)
        logger.info(f"민팅 신청 승인: ID {request_id}")
        return {"message": f"{request_id}번 신청이 승인되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"민팅 신청 승인 실패: {e}")
        raise HTTPException(status_code=500, detail="신청 승인 중 오류가 발생했습니다.")

@router.post("/reject/{request_id}")
def reject_request(request_id: int, db: Session = Depends(get_db)):
    if request_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 신청 ID입니다.")
    
    try:
        mint_req = db.query(MintRequest).filter(MintRequest.id == request_id).first()
        if not mint_req:
            raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
        if str(mint_req.status) != "pending":
            raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
        
        setattr(mint_req, 'status', 'rejected')
        db.commit()
        db.refresh(mint_req)
        logger.info(f"민팅 신청 거절: ID {request_id}")
        return {"message": f"{request_id}번 신청이 거절되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"민팅 신청 거절 실패: {e}")
        raise HTTPException(status_code=500, detail="신청 거절 중 오류가 발생했습니다.")

@router.post("/sync-upbit-transfers")
def sync_upbit_transfers(db: Session = Depends(get_db)):
    try:
        transfers = get_transfers()
        new_count = 0
        mint_count = 0
        burn_count = 0
        
        for t in transfers:
            if not isinstance(t, dict):
                logger.warning(f"유효하지 않은 전송 데이터: {t}")
                continue
                
            tx_id = t.get("tx_id")
            if not tx_id:
                logger.warning("tx_id가 없는 전송 데이터 건너뜀")
                continue
                
            exists = db.query(UpbitTransfer).filter(UpbitTransfer.tx_id == tx_id).first()
            if not exists:
                try:
                    upbit_tx = UpbitTransfer(
                        tx_id=tx_id,
                        type=t.get("type", ""),
                        amount=t.get("amount", 0),
                        currency=t.get("currency", ""),
                        status=t.get("status", ""),
                        created_at=t.get("created_at")
                    )
                    db.add(upbit_tx)
                    new_count += 1
                    # 입금이면 민팅 신청 생성 (중복 체크)
                    if t.get("type") == "deposit":
                        amount = t.get("amount", 0)
                        if amount > 0:
                            exists_mint = db.query(MintRequest).filter(
                                MintRequest.tx_id == tx_id,
                                MintRequest.amount == amount,
                                MintRequest.status.in_(["pending", "approved"])
                            ).first()
                            if not exists_mint:
                                db.add(MintRequest(
                                    eth_address="",  # 실제 입금자 주소 연동 필요
                                    amount=amount,
                                    tx_id=tx_id,
                                    status="pending"
                                ))
                                mint_count += 1
                    # 출금이면 소각 신청 생성 (중복 체크)
                    elif t.get("type") == "withdraw":
                        amount = t.get("amount", 0)
                        if amount > 0:
                            exists_burn = db.query(BurnRequest).filter(
                                BurnRequest.tx_id == tx_id,
                                BurnRequest.amount == amount,
                                BurnRequest.status.in_(["pending", "approved"])
                            ).first()
                            if not exists_burn:
                                db.add(BurnRequest(
                                    amount=amount,
                                    tx_id=tx_id,
                                    status="pending"
                                ))
                                burn_count += 1
                except Exception as e:
                    logger.error(f"전송 데이터 처리 실패: {e}, 데이터: {t}")
                    continue
        
        db.commit()
        logger.info(f"업비트 전송 동기화 완료: {new_count}건의 입출금 내역, {mint_count}건의 민팅 신청, {burn_count}건의 소각 신청")
        return {"message": f"{new_count}건의 입출금 내역, {mint_count}건의 민팅 신청, {burn_count}건의 소각 신청이 생성되었습니다."}
    except Exception as e:
        db.rollback()
        logger.error(f"업비트 전송 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"전송 동기화 중 오류가 발생했습니다: {str(e)}")

@router.get("/upbit-transfers")
def get_upbit_transfers(db: Session = Depends(get_db)):
    try:
        return db.query(UpbitTransfer).order_by(UpbitTransfer.created_at.desc()).all()
    except Exception as e:
        logger.error(f"업비트 전송 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="전송 내역 조회 중 오류가 발생했습니다.")

@router.post("/manual-burn")
def manual_burn(burn_request: ManualBurnRequest, db: Session = Depends(get_db)):
    try:
        burn = BurnRequest(
            amount=burn_request.amount,
            tx_id=burn_request.memo or "manual",
            status="pending"
        )
        db.add(burn)
        db.commit()
        db.refresh(burn)
        logger.info(f"수동 소각 신청 생성: ID {burn.id}, 금액 {burn_request.amount}")
        return {"message": "소각 신청이 생성되었습니다.", "id": burn.id, "amount": burn.amount}
    except Exception as e:
        db.rollback()
        logger.error(f"수동 소각 신청 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="소각 신청 생성 중 오류가 발생했습니다.")

@router.post("/approve-burn/{burn_id}")
def approve_burn(burn_id: int, db: Session = Depends(get_db)):
    if burn_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 소각 신청 ID입니다.")
    
    try:
        burn = db.query(BurnRequest).filter(BurnRequest.id == burn_id).first()
        if not burn:
            raise HTTPException(status_code=404, detail="소각 신청을 찾을 수 없습니다.")
        if str(burn.status) != "pending":
            raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
        
        setattr(burn, 'status', 'approved')
        db.commit()
        logger.info(f"소각 신청 승인: ID {burn_id}")
        return {"message": f"{burn_id}번 소각 신청이 승인되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"소각 신청 승인 실패: {e}")
        raise HTTPException(status_code=500, detail="소각 신청 승인 중 오류가 발생했습니다.")

@router.post("/reject-burn/{burn_id}")
def reject_burn(burn_id: int, db: Session = Depends(get_db)):
    if burn_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 소각 신청 ID입니다.")
    
    try:
        burn = db.query(BurnRequest).filter(BurnRequest.id == burn_id).first()
        if not burn:
            raise HTTPException(status_code=404, detail="소각 신청을 찾을 수 없습니다.")
        if str(burn.status) != "pending":
            raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
        
        setattr(burn, 'status', 'rejected')
        db.commit()
        logger.info(f"소각 신청 거절: ID {burn_id}")
        return {"message": f"{burn_id}번 소각 신청이 거절되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"소각 신청 거절 실패: {e}")
        raise HTTPException(status_code=500, detail="소각 신청 거절 중 오류가 발생했습니다.")

@router.get("/burn-requests")
def get_burn_requests(db: Session = Depends(get_db)):
    try:
        return db.query(BurnRequest).order_by(BurnRequest.created_at.desc()).all()
    except Exception as e:
        logger.error(f"소각 신청 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="소각 신청 목록 조회 중 오류가 발생했습니다.")

@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db)):
    try:
        total_minted_result = db.query(func.sum(MintRequest.amount)).filter(MintRequest.status == "approved").scalar()
        total_minted = float(total_minted_result) if total_minted_result is not None else 0.0
        
        total_burned_result = db.query(func.sum(BurnRequest.amount)).filter(BurnRequest.status == "approved").scalar()
        total_burned = float(total_burned_result) if total_burned_result is not None else 0.0
        
        usdt_balance = get_usdt_balance()
        circulating = total_minted - total_burned
        
        return {
            "usdt_balance": usdt_balance,
            "total_usdg_minted": total_minted,
            "total_usdg_burned": total_burned,
            "circulating_usdg": circulating
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")

@router.post("/check-balance-change")
def check_balance_change(db: Session = Depends(get_db)):
    try:
        current_balance = get_usdt_balance()
        
        # 가장 최근 잔액 기록 조회
        last_record = db.query(UpbitBalanceHistory).order_by(UpbitBalanceHistory.created_at.desc()).first()
        
        if last_record and hasattr(last_record, 'usdt_balance') and last_record.usdt_balance is not None:
            previous_balance = float(last_record.usdt_balance)
            change_amount = current_balance - previous_balance
            
            # 변화가 있는 경우에만 처리
            if abs(change_amount) > 0.000001:  # 최소 변화량 임계값
                # 입출금 내역으로 설명되는지 확인
                recent_transfers = db.query(UpbitTransfer).filter(
                    UpbitTransfer.created_at > last_record.created_at
                ).all()
                
                transfer_sum = 0.0
                for t in recent_transfers:
                    if hasattr(t, 'amount') and t.amount is not None:
                        amount_val = float(t.amount)
                        if hasattr(t, 'type') and t.type == 'deposit':
                            transfer_sum += amount_val
                        else:
                            transfer_sum -= amount_val
                
                # 입출금으로 설명되지 않는 변화 = 거래로 인한 변화
                unexplained_change = change_amount - transfer_sum
                
                if abs(unexplained_change) > 0.000001:
                    # 거래로 인한 변화로 민팅/소각 신청 생성
                    if unexplained_change > 0:
                        # USDT 증가 = 민팅 신청
                        db.add(MintRequest(
                            eth_address="",  # 거래로 인한 증가는 주소 없음
                            amount=unexplained_change,
                            status="pending"
                        ))
                        change_type = "trade_mint"
                    else:
                        # USDT 감소 = 소각 신청
                        db.add(BurnRequest(
                            amount=abs(unexplained_change),
                            tx_id="trade_burn",
                            status="pending"
                        ))
                        change_type = "trade_burn"
                    
                    # 잔액 변화 기록
                    db.add(UpbitBalanceHistory(
                        usdt_balance=current_balance,
                        change_amount=unexplained_change,
                        change_type=change_type
                    ))
                    
                    db.commit()
                    return {
                        "message": f"잔액 변화 감지: {unexplained_change:.6f} USDT",
                        "change_type": change_type,
                        "amount": abs(unexplained_change)
                    }
        
        # 최초 실행이거나 변화가 없는 경우
        db.add(UpbitBalanceHistory(
            usdt_balance=current_balance,
            change_amount=0,
            change_type="initial"
        ))
        db.commit()
        return {"message": "잔액 변화 없음"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"잔액 변화 감지 중 오류 발생: {str(e)}")