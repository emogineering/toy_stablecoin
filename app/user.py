from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models import MintRequest as MintRequestModel, get_db

router = APIRouter()

class MintRequest(BaseModel):
    eth_address: str
    amount: float

@router.post("/mint-request")
def mint_request(req: MintRequest, db: Session = Depends(get_db)):
    mint_req = MintRequestModel(
        eth_address=req.eth_address,
        amount=req.amount,
        status="pending"
    )
    db.add(mint_req)
    db.commit()
    db.refresh(mint_req)
    return {
        "message": "민팅 신청이 접수되었습니다.",
        "id": mint_req.id,
        "amount": mint_req.amount,
        "eth_address": mint_req.eth_address
    } 