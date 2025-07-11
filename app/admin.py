from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.models import MintRequest, UpbitTransfer, BurnRequest, get_db, UpbitBalanceHistory, UpbitTradeSync
from sqlalchemy import func
from app.upbit_api import get_usdt_balance
from app.upbit_api import get_transfers
from app.upbit_api import get_usdt_trades
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, validator
from typing import Optional
import logging
from apscheduler.schedulers.background import BackgroundScheduler

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

scheduler = None

# 거래 체결 폴링 백오프용 전역 변수
trade_poll_backoff_until = None


def start_scheduler():
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        
        def scheduled_balance_check():
            try:
                db = next(get_db())
                try:
                    check_balance_change(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"스케줄된 잔액 체크 중 오류: {e}")
        
        def scheduled_trade_poll():
            from datetime import datetime, timezone, timedelta
            global trade_poll_backoff_until
            now = datetime.now(timezone(timedelta(hours=9)))
            if trade_poll_backoff_until and now < trade_poll_backoff_until:
                logger.warning(f"[TRADE_POLL] 백오프 적용 중: {trade_poll_backoff_until}까지 폴링 일시 중지")
                return
            try:
                db = next(get_db())
                try:
                    poll_upbit_trades_and_trigger_mint_burn(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"스케줄된 거래 체결 폴링 중 오류: {e}")
                # 403 Forbidden 등 에러 발생 시 5분간 백오프
                if '403' in str(e):
                    trade_poll_backoff_until = now + timedelta(minutes=5)
                    logger.warning(f"[TRADE_POLL] 403 에러 발생, 5분간 폴링 중지: {trade_poll_backoff_until}")
        
        scheduler.add_job(scheduled_balance_check, 'interval', seconds=5)
        scheduler.add_job(scheduled_trade_poll, 'interval', seconds=60)  # 60초마다 거래 체결 폴링
        scheduler.start()

def poll_upbit_trades_and_trigger_mint_burn(db: Session):
    """업비트 거래 체결 내역을 폴링하여 새로운 매수/매도에 따라 민팅/소각 신청을 자동 생성한다."""
    try:
        # 1. 마지막으로 처리한 체결 UUID 조회
        sync_record = db.query(UpbitTradeSync).first()
        last_processed_uuid = None
        if sync_record and hasattr(sync_record, 'last_trade_uuid') and sync_record.last_trade_uuid:
            last_processed_uuid = sync_record.last_trade_uuid
        
        # 2. 최근 거래 체결 내역 조회
        trades = get_usdt_trades()
        logger.info(f"[TRADE_POLL] 조회된 체결 내역: {len(trades)}건")
        
        if not trades:
            logger.info("[TRADE_POLL] 처리할 체결 내역이 없습니다.")
            return
        
        # 3. 마지막 처리 UUID 이후의 새로운 체결만 필터링
        new_trades = []
        if last_processed_uuid:
            for trade in trades:
                if trade['uuid'] != last_processed_uuid:
                    new_trades.append(trade)
                else:
                    break  # 마지막 처리 UUID를 만나면 중단
        else:
            # 첫 실행인 경우 가장 최근 체결 1건만 처리 (초기 동기화 방지)
            new_trades = trades[:1] if trades else []
        
        if not new_trades:
            logger.info("[TRADE_POLL] 새로운 체결 내역이 없습니다.")
            return
        
        logger.info(f"[TRADE_POLL] 새로운 체결 내역: {len(new_trades)}건")
        
        # 4. 각 체결에 따라 민팅/소각 신청 생성
        latest_uuid = None
        for trade in new_trades:
            latest_uuid = trade['uuid']
            side = trade['side']  # bid(매수), ask(매도)
            volume = trade['volume']  # USDT 수량
            price = trade['price']  # KRW 가격
            created_at = trade['created_at']
            
            logger.info(f"[TRADE_POLL] 체결 처리: {side}, 수량: {volume} USDT, 가격: {price} KRW")
            
            if side == 'bid':  # 매수 = USDT 증가 = 민팅 신청
                # 중복 체크: 최근 1시간 내 동일한 체결 UUID로 생성된 민팅 신청이 있는지 확인
                existing_mint = db.query(MintRequest).filter(
                    MintRequest.tx_id == f"trade_{latest_uuid}",
                    MintRequest.status.in_(["pending", "approved"]),
                    MintRequest.created_at >= (datetime.now(timezone(timedelta(hours=9))) - timedelta(hours=1))
                ).first()
                
                if not existing_mint:
                    db.add(MintRequest(
                        eth_address="",
                        amount=volume,
                        tx_id=f"trade_{latest_uuid}",
                        status="pending"
                    ))
                    logger.info(f"[TRADE_POLL] 매수 체결로 인한 민팅 신청 생성: {volume} USDT, tx_id=trade_{latest_uuid}")
                else:
                    logger.info(f"[TRADE_POLL] 이미 처리된 매수 체결: {latest_uuid}")
            
            elif side == 'ask':  # 매도 = USDT 감소 = 소각 신청
                # 중복 체크: 최근 1시간 내 동일한 체결 UUID로 생성된 소각 신청이 있는지 확인
                existing_burn = db.query(BurnRequest).filter(
                    BurnRequest.tx_id == f"trade_{latest_uuid}",
                    BurnRequest.status.in_(["pending", "approved"]),
                    BurnRequest.created_at >= (datetime.now(timezone(timedelta(hours=9))) - timedelta(hours=1))
                ).first()
                
                if not existing_burn:
                    db.add(BurnRequest(
                        amount=volume,
                        tx_id=f"trade_{latest_uuid}",
                        status="pending"
                    ))
                    logger.info(f"[TRADE_POLL] 매도 체결로 인한 소각 신청 생성: {volume} USDT, tx_id=trade_{latest_uuid}")
                else:
                    logger.info(f"[TRADE_POLL] 이미 처리된 매도 체결: {latest_uuid}")
        
        # 5. 마지막 처리 UUID 갱신
        if latest_uuid:
            if sync_record:
                setattr(sync_record, 'last_trade_uuid', latest_uuid)
                setattr(sync_record, 'last_checked_at', datetime.now(timezone(timedelta(hours=9))))
            else:
                db.add(UpbitTradeSync(
                    last_trade_uuid=latest_uuid,
                    last_checked_at=datetime.now(timezone(timedelta(hours=9)))
                ))
            
            db.commit()
            logger.info(f"[TRADE_POLL] 마지막 처리 UUID 갱신: {latest_uuid}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"[TRADE_POLL] 거래 체결 폴링 중 오류 발생: {e}")
        raise

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
    start_scheduler()

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
        logger.info(f"[SYNC] 업비트 입출금 내역: {transfers}")
        new_count = 0
        mint_count = 0
        burn_count = 0
        
        for t in transfers:
            if not isinstance(t, dict):
                logger.warning(f"유효하지 않은 전송 데이터: {t}")
                continue
            tx_id = t.get("tx_id")
            if not tx_id:
                logger.warning(f"tx_id가 없는 전송 데이터 건너뜀: {t}")
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
                    logger.info(f"[SYNC] UpbitTransfer 저장: {upbit_tx}")
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
                                logger.info(f"[SYNC] MintRequest 생성: amount={amount}, tx_id={tx_id}")
                            else:
                                logger.warning(f"[SYNC] 중복 민팅 신청 감지: amount={amount}, tx_id={tx_id}")
                        else:
                            logger.warning(f"[SYNC] 0 이하 금액의 입금 민팅 무시: {t}")
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
                                logger.info(f"[SYNC] BurnRequest 생성: amount={amount}, tx_id={tx_id}")
                            else:
                                logger.warning(f"[SYNC] 중복 소각 신청 감지: amount={amount}, tx_id={tx_id}")
                        else:
                            logger.warning(f"[SYNC] 0 이하 금액의 출금 소각 무시: {t}")
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

        # 24시간 변화량 계산
        now = datetime.now(timezone(timedelta(hours=9)))  # KST
        since = now - timedelta(hours=24)
        history = db.query(UpbitBalanceHistory).filter(UpbitBalanceHistory.created_at >= since).all()
        last_24h_balance_change = sum([float(h.change_amount) for h in history]) if len(history) > 0 else 0.0

        return {
            "usdt_balance": usdt_balance,
            "total_usdg_minted": total_minted,
            "total_usdg_burned": total_burned,
            "circulating_usdg": circulating,
            "last_24h_balance_change": last_24h_balance_change
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")

@router.post("/check-balance-change")
def check_balance_change(db: Session = Depends(get_db)):
    try:
        current_balance = get_usdt_balance()
        logger.info(f"[BALANCE] 현재 USDT 잔액: {current_balance}")
        last_record = db.query(UpbitBalanceHistory).order_by(UpbitBalanceHistory.created_at.desc()).first()
        if last_record and hasattr(last_record, 'usdt_balance') and last_record.usdt_balance is not None:
            previous_balance = float(last_record.usdt_balance)
            change_amount = current_balance - previous_balance
            logger.info(f"[BALANCE] 이전 잔액: {previous_balance}, 변화량: {change_amount}")
            if abs(change_amount) > 0.000001:
                now = datetime.now(timezone(timedelta(hours=9)))  # KST
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
                unexplained_change = change_amount - transfer_sum
                logger.info(f"[BALANCE] 입출금으로 설명되지 않는 변화: {unexplained_change}")
                if abs(unexplained_change) > 0.000001:
                    if unexplained_change > 0:
                        # USDT 증가 = 민팅 신청 (중복 체크 추가)
                        # 최근 1시간 내에 같은 금액의 trade_mint 민팅 신청이 있는지 확인
                        recent_mint = db.query(MintRequest).filter(
                            MintRequest.amount == unexplained_change,
                            MintRequest.tx_id.is_(None),  # tx_id가 없는 trade_mint
                            MintRequest.status.in_(["pending", "approved"]),
                            MintRequest.created_at >= (now - timedelta(hours=1))
                        ).first()
                        
                        if not recent_mint:
                            db.add(MintRequest(
                                eth_address="",
                                amount=unexplained_change,
                                status="pending"
                            ))
                            logger.info(f"[BALANCE] 입출금 내역으로 설명되지 않는 민팅 자동 생성: amount={unexplained_change}, tx_id 없음")
                            change_type = "trade_mint"
                        else:
                            logger.info(f"[BALANCE] 최근 1시간 내 동일한 trade_mint 민팅 신청 존재: amount={unexplained_change}")
                            change_type = "trade_mint_duplicate"
                    else:
                        # USDT 감소 = 소각 신청 (중복 체크 추가)
                        recent_burn = db.query(BurnRequest).filter(
                            BurnRequest.amount == abs(unexplained_change),
                            BurnRequest.tx_id == "trade_burn",
                            BurnRequest.status.in_(["pending", "approved"]),
                            BurnRequest.created_at >= (now - timedelta(hours=1))
                        ).first()
                        
                        if not recent_burn:
                            db.add(BurnRequest(
                                amount=abs(unexplained_change),
                                tx_id="trade_burn",
                                status="pending"
                            ))
                            logger.info(f"[BALANCE] 입출금 내역으로 설명되지 않는 소각 자동 생성: amount={abs(unexplained_change)}, tx_id=trade_burn")
                            change_type = "trade_burn"
                        else:
                            logger.info(f"[BALANCE] 최근 1시간 내 동일한 trade_burn 소각 신청 존재: amount={abs(unexplained_change)}")
                            change_type = "trade_burn_duplicate"
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
        db.add(UpbitBalanceHistory(
            usdt_balance=current_balance,
            change_amount=0,
            change_type="initial"
        ))
        db.commit()
        logger.info("[BALANCE] 잔액 변화 없음 기록")
        return {"message": "잔액 변화 없음"}
    except Exception as e:
        db.rollback()
        logger.error(f"잔액 변화 감지 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"잔액 변화 감지 중 오류 발생: {str(e)}")

@router.post("/poll-trades")
def poll_trades(db: Session = Depends(get_db)):
    """수동으로 거래 체결 폴링을 실행한다."""
    try:
        poll_upbit_trades_and_trigger_mint_burn(db)
        return {"message": "거래 체결 폴링이 완료되었습니다."}
    except Exception as e:
        logger.error(f"거래 체결 폴링 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"거래 체결 폴링 중 오류 발생: {str(e)}")

@router.get("/trade-sync-status")
def get_trade_sync_status(db: Session = Depends(get_db)):
    """거래 체결 동기화 상태를 조회한다."""
    try:
        sync_record = db.query(UpbitTradeSync).first()
        if sync_record:
            return {
                "last_trade_uuid": sync_record.last_trade_uuid,
                "last_checked_at": sync_record.last_checked_at
            }
        else:
            return {
                "last_trade_uuid": None,
                "last_checked_at": None,
                "message": "아직 동기화된 거래가 없습니다."
            }
    except Exception as e:
        logger.error(f"거래 동기화 상태 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"거래 동기화 상태 조회 중 오류 발생: {str(e)}")