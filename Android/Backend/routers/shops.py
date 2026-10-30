from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Shop, User
from schemas import ShopResponse, ShopCreateRequest
from firebase_auth import authenticated_user, require_role

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.get("/me", response_model=ShopResponse | None)
def get_current_shop(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    """Read the caller's shop without creating placeholder production records."""
    require_role(user, "shop_owner", "shopkeeper")
    shop = db.query(Shop).filter(Shop.owner_id == user.id).order_by(Shop.created_at.asc()).first()
    return ShopResponse.from_orm(shop) if shop else None

@router.put("/me", response_model=ShopResponse, status_code=status.HTTP_200_OK)
def save_current_shop(request: ShopCreateRequest, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    """Create or update the shop bound to the verified owner identity."""
    require_role(user, "shop_owner", "shopkeeper")
    name = request.shop_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Shop name cannot be blank")
    shop = db.query(Shop).filter(Shop.owner_id == user.id).order_by(Shop.created_at.asc()).first()
    if shop is None:
        shop = Shop(owner_id=user.id, shop_name=name, address=request.address, category=request.category)
        db.add(shop)
    else:
        shop.shop_name = name
        shop.address = request.address
        shop.category = request.category
    db.commit()
    db.refresh(shop)
    return ShopResponse.from_orm(shop)

@router.get("/me/{owner_phone}", response_model=ShopResponse)
def get_my_shop(owner_phone: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")

    shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop profile not found")
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
