from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Shop, User
from schemas import ShopResponse, ShopCreateRequest
from firebase_auth import authenticated_user, require_role

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.get("/me/{owner_phone}", response_model=ShopResponse)
def get_my_shop(owner_phone: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")

    shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
    if not shop:
        shop = Shop(owner_id=user.id, shop_name="Rahul General Store")
        db.add(shop)
        db.commit()
        db.refresh(shop)

    return ShopResponse.from_orm(shop)

@router.patch("/me/{owner_phone}", response_model=ShopResponse)
def update_my_shop(owner_phone: str, request: ShopCreateRequest, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")

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
