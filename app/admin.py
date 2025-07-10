from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.models import MintRequest, UpbitTransfer, BurnRequest, get_db, UpbitBalanceHistory
from sqlalchemy import func
from app.upbit_api import get_usdt_balance
from app.upbit_api import get_transfers
from datetime import datetime

router = APIRouter()

@router.get("/mint-requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(MintRequest).order_by(MintRequest.created_at.desc()).all()

@router.post("/approve/{request_id}")
def approve_request(request_id: int, db: Session = Depends(get_db)):
    mint_req = db.query(MintRequest).filter(MintRequest.id == request_id).first()
    if not mint_req:
        raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
    if str(mint_req.status) != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
    setattr(mint_req, 'status', 'approved')
    db.commit()
    db.refresh(mint_req)
    return {"message": f"{request_id}번 신청이 승인되었습니다."}

@router.post("/sync-upbit-transfers")
def sync_upbit_transfers(db: Session = Depends(get_db)):
    transfers = get_transfers()
    new_count = 0
    mint_count = 0
    burn_count = 0
    for t in transfers:
        exists = db.query(UpbitTransfer).filter(UpbitTransfer.tx_id == t["tx_id"]).first()
        if not exists:
            upbit_tx = UpbitTransfer(
                tx_id=t["tx_id"],
                type=t["type"],
                amount=t["amount"],
                currency=t["currency"],
                status=t["status"],
                created_at=t["created_at"]
            )
            db.add(upbit_tx)
            new_count += 1
            # 입금이면 민팅 신청 생성
            if t["type"] == "deposit":
                db.add(MintRequest(
                    eth_address="",  # 실제 입금자 주소 연동 필요
                    amount=t["amount"],
                    status="pending"
                ))
                mint_count += 1
            # 출금이면 소각 신청 생성
            elif t["type"] == "withdraw":
                db.add(BurnRequest(
                    amount=t["amount"],
                    tx_id=t["tx_id"],
                    status="pending"
                ))
                burn_count += 1
    db.commit()
    return {"message": f"{new_count}건의 입출금 내역, {mint_count}건의 민팅 신청, {burn_count}건의 소각 신청이 생성되었습니다."}

@router.get("/upbit-transfers")
def get_upbit_transfers(db: Session = Depends(get_db)):
    return db.query(UpbitTransfer).order_by(UpbitTransfer.created_at.desc()).all()

@router.post("/manual-burn")
def manual_burn(amount: float = Body(...), memo: str = Body(None), db: Session = Depends(get_db)):
    burn = BurnRequest(
        amount=amount,
        tx_id=memo or "manual",
        status="pending"
    )
    db.add(burn)
    db.commit()
    db.refresh(burn)
    return {"message": "소각 신청이 생성되었습니다.", "id": burn.id, "amount": burn.amount}

@router.post("/approve-burn/{burn_id}")
def approve_burn(burn_id: int, db: Session = Depends(get_db)):
    burn = db.query(BurnRequest).filter(BurnRequest.id == burn_id).first()
    if not burn:
        raise HTTPException(status_code=404, detail="소각 신청을 찾을 수 없습니다.")
    if str(burn.status) != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
    setattr(burn, 'status', 'approved')
    db.commit()
    return {"message": f"{burn_id}번 소각 신청이 승인되었습니다."}

@router.post("/reject-burn/{burn_id}")
def reject_burn(burn_id: int, db: Session = Depends(get_db)):
    burn = db.query(BurnRequest).filter(BurnRequest.id == burn_id).first()
    if not burn:
        raise HTTPException(status_code=404, detail="소각 신청을 찾을 수 없습니다.")
    if str(burn.status) != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
    setattr(burn, 'status', 'rejected')
    db.commit()
    return {"message": f"{burn_id}번 소각 신청이 거절되었습니다."}

@router.get("/burn-requests")
def get_burn_requests(db: Session = Depends(get_db)):
    return db.query(BurnRequest).order_by(BurnRequest.created_at.desc()).all()

@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total_minted = db.query(func.sum(MintRequest.amount)).filter(MintRequest.status == "approved").scalar() or 0
    total_burned = db.query(func.sum(BurnRequest.amount)).filter(BurnRequest.status == "approved").scalar() or 0
    usdt_balance = get_usdt_balance()
    circulating = total_minted - total_burned
    return {
        "usdt_balance": usdt_balance,
        "total_usdg_minted": total_minted,
        "total_usdg_burned": total_burned,
        "circulating_usdg": circulating
    }

@router.post("/check-balance-change")
def check_balance_change(db: Session = Depends(get_db)):
    current_balance = get_usdt_balance()
    
    # 가장 최근 잔액 기록 조회
    last_record = db.query(UpbitBalanceHistory).order_by(UpbitBalanceHistory.created_at.desc()).first()
    
    if last_record:
        previous_balance = float(last_record.usdt_balance)
        change_amount = current_balance - previous_balance
        
        # 변화가 있는 경우에만 처리
        if abs(change_amount) > 0.000001:  # 최소 변화량 임계값
            # 입출금 내역으로 설명되는지 확인
            recent_transfers = db.query(UpbitTransfer).filter(
                UpbitTransfer.created_at > last_record.created_at
            ).all()
            
            transfer_sum = sum(float(t.amount) if t.type == 'deposit' else -float(t.amount) for t in recent_transfers)
            
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