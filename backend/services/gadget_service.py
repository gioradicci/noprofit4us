from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from typing import Optional
from database.models.gadget import Gadget, Warehouse, GadgetVariantStock, StockMovement, GadgetLock
from services.audit_service import log_action
from datetime import datetime, timedelta

def acquire_lock(db: Session, gadget_id: int, user_id: int) -> bool:
    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")
        
    lock = db.query(GadgetLock).filter(GadgetLock.gadget_id == gadget_id).first()
    now = datetime.utcnow()
    
    if lock:
        if lock.user_id != user_id and lock.expires_at > now:
            user_name = f"{lock.user.first_name or ''} {lock.user.last_name or ''}".strip() if lock.user else None
            if not user_name:
                user_name = lock.user.email if lock.user and lock.user.email else f"Utente {lock.user_id}"
            raise HTTPException(
                status_code=423, 
                detail=f"Questo articolo è attualmente in modifica da parte di {user_name}."
            )
        # Refresh existing lock
        lock.user_id = user_id
        lock.locked_at = now
        lock.expires_at = now + timedelta(minutes=3)
    else:
        # Create new lock
        lock = GadgetLock(
            gadget_id=gadget_id,
            user_id=user_id,
            locked_at=now,
            expires_at=now + timedelta(minutes=3)
        )
        db.add(lock)
        
    db.commit()
    return True

def release_lock(db: Session, gadget_id: int, user_id: int) -> bool:
    lock = db.query(GadgetLock).filter(GadgetLock.gadget_id == gadget_id).first()
    if lock and lock.user_id == user_id:
        db.delete(lock)
        db.commit()
    return True

def create_gadget(
    db: Session,
    name: str,
    category: str,
    min_donation: float,
    description: Optional[str] = None,
    image_path: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    model: Optional[str] = None,
    variant_type: Optional[str] = None,
    sku: Optional[str] = None,
    price_modifier: float = 0.0,
    performed_by: Optional[int] = None
) -> Gadget:
    gadget = Gadget(
        name=name,
        description=description,
        category=category,
        min_donation=min_donation,
        image_path=image_path,
        size=size,
        color=color,
        model=model,
        variant_type=variant_type,
        sku=sku,
        price_modifier=price_modifier or 0.0,
        stock_quantity=0
    )
    db.add(gadget)
    db.commit()
    db.refresh(gadget)

    log_action(
        db=db,
        action_type="CREATE_GADGET",
        entity_type="GADGET",
        entity_id=gadget.id,
        performed_by=performed_by,
        details=f"Created gadget '{gadget.name}' (SKU: {gadget.sku}, Category: {gadget.category})"
    )
    db.commit()
    return gadget

def delete_gadget(db: Session, gadget_id: int, performed_by: int) -> bool:
    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    if (gadget.stock_quantity or 0) > 0:
        raise HTTPException(status_code=400, detail="Impossibile eliminare il gadget perché ci sono ancora pezzi in magazzino.")

    gadget_name = gadget.name
    db.delete(gadget)
    db.commit()

    log_action(
        db=db,
        action_type="DELETE_GADGET",
        entity_type="GADGET",
        entity_id=gadget_id,
        performed_by=performed_by,
        details=f"Deleted gadget '{gadget_name}'"
    )
    db.commit()
    return True


def update_gadget(
    db: Session,
    gadget_id: int,
    name: str,
    category: str,
    min_donation: float,
    description: Optional[str] = None,
    image_path: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    model: Optional[str] = None,
    variant_type: Optional[str] = None,
    sku: Optional[str] = None,
    price_modifier: float = 0.0,
    performed_by: Optional[int] = None
) -> Gadget:
    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    gadget.name = name
    gadget.category = category
    gadget.min_donation = min_donation
    gadget.description = description
    gadget.image_path = image_path
    gadget.size = size
    gadget.color = color
    gadget.model = model
    gadget.variant_type = variant_type
    gadget.sku = sku
    gadget.price_modifier = price_modifier or 0.0

    db.commit()
    db.refresh(gadget)

    log_action(
        db=db,
        action_type="UPDATE_GADGET",
        entity_type="GADGET",
        entity_id=gadget.id,
        performed_by=performed_by,
        details=f"Updated gadget '{gadget.name}' (SKU: {gadget.sku}, Category: {gadget.category})"
    )
    db.commit()
    return gadget


def create_stock_movement(
    db: Session,
    gadget_id: int,
    quantity: int,
    movement_type: str,
    performed_by: int,
    from_warehouse_id: Optional[int] = None,
    to_warehouse_id: Optional[int] = None,
    notes: Optional[str] = None
) -> StockMovement:
    # Validate type
    if movement_type not in ["RESTOCK", "TRANSFER", "DELIVERY"]:
        raise HTTPException(status_code=400, detail="Invalid movement type")

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    # Validate warehouse requirements
    if movement_type == "TRANSFER":
        if not from_warehouse_id or not to_warehouse_id:
            raise HTTPException(status_code=400, detail="Both source and destination warehouses are required for transfers")
        if from_warehouse_id == to_warehouse_id:
            raise HTTPException(status_code=400, detail="Il magazzino di origine e destinazione devono essere diversi.")
    elif movement_type == "RESTOCK":
        if not to_warehouse_id:
            raise HTTPException(status_code=400, detail="Destination warehouse is required for restocks")
    elif movement_type == "DELIVERY":
        if not from_warehouse_id:
            raise HTTPException(status_code=400, detail="Source warehouse is required for deliveries")

    # Apply changes
    # 1. Deduct stock from source warehouse
    if from_warehouse_id:
        stock_from = db.query(GadgetVariantStock).filter_by(
            gadget_id=gadget_id, warehouse_id=from_warehouse_id
        ).first()
        if not stock_from or stock_from.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock in source warehouse")
        stock_from.quantity -= quantity

    # 2. Add stock to destination warehouse
    if to_warehouse_id:
        stock_to = db.query(GadgetVariantStock).filter_by(
            gadget_id=gadget_id, warehouse_id=to_warehouse_id
        ).first()
        if not stock_to:
            stock_to = GadgetVariantStock(
                gadget_id=gadget_id,
                warehouse_id=to_warehouse_id,
                quantity=0
            )
            db.add(stock_to)
        stock_to.quantity += quantity

    # 3. Create movement log
    movement = StockMovement(
        gadget_id=gadget_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        quantity=quantity,
        movement_type=movement_type,
        performed_by=performed_by,
        notes=notes
    )
    db.add(movement)
    db.flush()

    # 4. Update total aggregated stock on gadget
    total_stock = db.query(func.sum(GadgetVariantStock.quantity)).filter_by(gadget_id=gadget.id).scalar() or 0
    gadget.stock_quantity = total_stock

    db.commit()

    log_action(
        db=db,
        action_type="STOCK_MOVEMENT",
        entity_type="STOCK_MOVEMENT",
        entity_id=movement.id,
        performed_by=performed_by,
        details=f"Stock movement: {movement_type} (Quantity: {quantity}) for Gadget '{gadget.name}' (SKU: {gadget.sku or gadget.id})"
    )
    db.commit()
    return movement


def bulk_transfer_warehouse_stock(
    db: Session,
    from_warehouse_id: int,
    to_warehouse_id: int,
    performed_by: int,
    notes: Optional[str] = None
) -> int:
    if from_warehouse_id == to_warehouse_id:
        raise HTTPException(status_code=400, detail="Il magazzino di origine e destinazione devono essere diversi.")

    from_wh = db.query(Warehouse).get(from_warehouse_id)
    to_wh = db.query(Warehouse).get(to_warehouse_id)
    if not from_wh or not to_wh:
        raise HTTPException(status_code=404, detail="Magazzino di origine o destinazione non trovato.")

    if not to_wh.is_active:
        raise HTTPException(status_code=400, detail="Il magazzino di destinazione deve essere attivo.")

    # Find all stock rows in from_warehouse that have quantity > 0
    active_stocks = db.query(GadgetVariantStock).filter(
        GadgetVariantStock.warehouse_id == from_warehouse_id,
        GadgetVariantStock.quantity > 0
    ).all()

    if not active_stocks:
        return 0

    transferred_count = 0
    for stock in active_stocks:
        qty = stock.quantity
        gadget_id = stock.gadget_id
        
        # Deduct from source
        stock.quantity = 0

        # Add to destination
        stock_to = db.query(GadgetVariantStock).filter_by(
            gadget_id=gadget_id, warehouse_id=to_warehouse_id
        ).first()
        if not stock_to:
            stock_to = GadgetVariantStock(
                gadget_id=gadget_id,
                warehouse_id=to_warehouse_id,
                quantity=0
            )
            db.add(stock_to)
        stock_to.quantity += qty

        # Record movement log
        movement = StockMovement(
            gadget_id=gadget_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            quantity=qty,
            movement_type="TRANSFER",
            performed_by=performed_by,
            notes=notes or f"Spostamento massivo da {from_wh.code} a {to_wh.code}"
        )
        db.add(movement)
        
        transferred_count += qty

    db.commit()

    log_action(
        db=db,
        action_type="BULK_STOCK_TRANSFER",
        entity_type="WAREHOUSE",
        entity_id=from_warehouse_id,
        performed_by=performed_by,
        details=f"Bulk stock transfer from warehouse {from_wh.code} (ID: {from_warehouse_id}) to {to_wh.code} (ID: {to_warehouse_id}). Total items: {transferred_count}."
    )
    db.commit()

    return transferred_count


