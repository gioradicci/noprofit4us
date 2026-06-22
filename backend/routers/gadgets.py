from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database.database import get_db
from database.models.gadget import Gadget, Warehouse, StockMovement
from dependencies.auth import get_current_user
from services import gadget_service
from database.models.member import Member
from database.models.membership import Membership
from datetime import date

#router = APIRouter(prefix="/gadgets", tags=["gadgets"])
router = APIRouter()

def has_active_membership(user, db: Session) -> bool:
    member = db.query(Member).filter_by(user_id=user.id).first()
    if not member:
        return False
    active_membership = db.query(Membership).filter(
        Membership.member_id == member.id,
        Membership.is_paid == True,
        Membership.end_date >= date.today()
    ).first()
    return active_membership is not None


# Pydantic Schemas
class GadgetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    min_donation: float

class VariantCreate(BaseModel):
    gadget_id: int
    size: Optional[str] = None
    color: Optional[str] = None
    model: Optional[str] = None
    variant_type: Optional[str] = None
    sku: Optional[str] = None
    price_modifier: Optional[float] = 0.0

class GadgetUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    min_donation: float

class VariantUpdate(BaseModel):
    id: Optional[int] = None
    size: Optional[str] = None
    color: Optional[str] = None
    model: Optional[str] = None
    variant_type: Optional[str] = None
    sku: Optional[str] = None
    price_modifier: Optional[float] = 0.0

class MovementCreate(BaseModel):
    variant_id: int
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    quantity: int
    movement_type: str  # RESTOCK, TRANSFER, DELIVERY
    notes: Optional[str] = None


@router.get("/")
def get_gadgets(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    gadgets = db.query(Gadget).all()
    result = []
    for g in gadgets:
        g_data = {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "category": g.category,
            "min_donation": g.min_donation,
            "created_at": g.created_at.isoformat() if g.created_at else None,
            "variants": []
        }
        for v in g.variants:
            v_data = {
                "id": v.id,
                "size": v.size,
                "color": v.color,
                "model": v.model,
                "variant_type": v.variant_type,
                "sku": v.sku,
                "price_modifier": v.price_modifier,
                "stock_quantity": v.stock_quantity,
                "stocks": []
            }
            for s in v.stocks:
                v_data["stocks"].append({
                    "warehouse_id": s.warehouse_id,
                    "warehouse_name": s.warehouse.name,
                    "warehouse_code": s.warehouse.code,
                    "quantity": s.quantity
                })
            g_data["variants"].append(v_data)
        result.append(g_data)
    return result


@router.post("/")
def create_gadget(payload: GadgetCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    gadget = gadget_service.create_gadget(
        db=db,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        min_donation=payload.min_donation,
        performed_by=current_user.id
    )
    return {
        "id": gadget.id,
        "name": gadget.name,
        "description": gadget.description,
        "category": gadget.category,
        "min_donation": gadget.min_donation,
        "created_at": gadget.created_at.isoformat() if gadget.created_at else None
    }


@router.post("/variants")
def create_variant(payload: VariantCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    variant = gadget_service.create_variant(
        db=db,
        gadget_id=payload.gadget_id,
        size=payload.size,
        color=payload.color,
        model=payload.model,
        variant_type=payload.variant_type,
        sku=payload.sku,
        price_modifier=payload.price_modifier or 0.0,
        performed_by=current_user.id
    )
    return {
        "id": variant.id,
        "gadget_id": variant.gadget_id,
        "size": variant.size,
        "color": variant.color,
        "model": variant.model,
        "variant_type": variant.variant_type,
        "sku": variant.sku,
        "price_modifier": variant.price_modifier
    }


@router.put("/{id}")
def update_gadget(id: int, payload: GadgetUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    gadget = gadget_service.update_gadget(
        db=db,
        gadget_id=id,
        name=payload.name,
        category=payload.category,
        min_donation=payload.min_donation,
        description=payload.description,
        performed_by=current_user.id
    )
    return {
        "id": gadget.id,
        "name": gadget.name,
        "description": gadget.description,
        "category": gadget.category,
        "min_donation": gadget.min_donation,
        "created_at": gadget.created_at.isoformat() if gadget.created_at else None
    }


@router.put("/{gadget_id}/variants")
def update_gadget_variants(gadget_id: int, payload: List[VariantUpdate], current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    updated_variants = gadget_service.update_gadget_variants(
        db=db,
        gadget_id=gadget_id,
        variants_data=[v.dict() for v in payload],
        performed_by=current_user.id
    )
    return [
        {
            "id": v.id,
            "gadget_id": v.gadget_id,
            "size": v.size,
            "color": v.color,
            "model": v.model,
            "variant_type": v.variant_type,
            "sku": v.sku,
            "price_modifier": v.price_modifier,
            "stock_quantity": v.stock_quantity
        }
        for v in updated_variants
    ]


@router.delete("/{id}")
def delete_gadget(id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    gadget_service.delete_gadget(
        db=db,
        gadget_id=id,
        performed_by=current_user.id
    )
    return {"status": "deleted"}


@router.get("/warehouses")
def get_warehouses(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")
    return db.query(Warehouse).all()


@router.get("/movements")
def get_movements(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    movements = db.query(StockMovement).order_by(StockMovement.timestamp.desc()).all()
    result = []
    for m in movements:
        result.append({
            "id": m.id,
            "variant_id": m.variant_id,
            "variant_sku": m.variant.sku if m.variant else None,
            "gadget_name": m.variant.gadget.name if m.variant and m.variant.gadget else None,
            "from_warehouse": {
                "id": m.from_warehouse.id,
                "name": m.from_warehouse.name,
                "code": m.from_warehouse.code
            } if m.from_warehouse else None,
            "to_warehouse": {
                "id": m.to_warehouse.id,
                "name": m.to_warehouse.name,
                "code": m.to_warehouse.code
            } if m.to_warehouse else None,
            "quantity": m.quantity,
            "movement_type": m.movement_type,
            "performed_by": m.performed_by,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "notes": m.notes
        })
    return result


@router.post("/movements")
def create_movement(payload: MovementCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["ADMIN", "SECRETARY"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role == "SECRETARY" and not has_active_membership(current_user, db):
        raise HTTPException(status_code=403, detail="Active membership required")

    movement = gadget_service.create_stock_movement(
        db=db,
        variant_id=payload.variant_id,
        from_warehouse_id=payload.from_warehouse_id,
        to_warehouse_id=payload.to_warehouse_id,
        quantity=payload.quantity,
        movement_type=payload.movement_type,
        performed_by=current_user.id,
        notes=payload.notes
    )
    return {"status": "success", "movement_id": movement.id}
