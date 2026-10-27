from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Shop, User
from schemas import ShopResponse, ShopCreateRequest

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.get("/me/{owner_phone}", response_model=ShopResponse)
def get_my_shop(owner_phone: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == owner_phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
    if not shop:
        shop = Shop(owner_id=user.id, shop_name="Rahul General Store")
        db.add(shop)
        db.commit()
        db.refresh(shop)

    return ShopResponse.from_orm(shop)

@router.patch("/me/{owner_phone}", response_model=ShopResponse)
def update_my_shop(owner_phone: str, request: ShopCreateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == owner_phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
    if not shop:
        shop = Shop(
            owner_id=user.id,
            shop_name=request.shop_name,
            address=request.address,
            category=request.category
        )
        db.add(shop)
    else:
        shop.shop_name = request.shop_name
        if request.address:
            shop.address = request.address
        if request.category:
            shop.category = request.category

    db.commit()
    db.refresh(shop)

    return ShopResponse.from_orm(shop)
