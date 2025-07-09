from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import MintRequest as MintRequestModel, get_db

router = APIRouter()

@router.get("/mint-requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(MintRequestModel).all()

@router.post("/approve/{request_id}")
def approve_request(request_id: int, db: Session = Depends(get_db)):
    mint_req = db.query(MintRequestModel).filter(MintRequestModel.id == request_id).first()
    if not mint_req:
        raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
    if str(mint_req.status) != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 신청입니다.")
    setattr(mint_req, 'status', 'approved')
    db.commit()
    db.refresh(mint_req)
    return {"message": f"{request_id}번 신청이 승인되었습니다."} 