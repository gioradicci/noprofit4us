from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from typing import Optional
from database.models.gadget import Gadget, GadgetVariant, Warehouse, GadgetVariantStock, StockMovement
from services.audit_service import log_action



def create_gadget(
    db: Session,
    name: str,
    category: str,
    min_donation: float,
    description: Optional[str] = None,
    image_path: Optional[str] = None,
    performed_by: Optional[int] = None
) -> Gadget:
    gadget = Gadget(
        name=name,
        description=description,
        category=category,
        min_donation=min_donation,
        image_path=image_path
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
        details=f"Created gadget '{gadget.name}' (Category: {gadget.category})"
    )
    db.commit()
    return gadget

def create_variant(
    db: Session,
    gadget_id: int,
    size: Optional[str] = None,
    color: Optional[str] = None,
    model: Optional[str] = None,
    variant_type: Optional[str] = None,
    sku: Optional[str] = None,
    price_modifier: float = 0.0,
    image_path: Optional[str] = None,
    performed_by: Optional[int] = None
) -> GadgetVariant:
    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    variant = GadgetVariant(
        gadget_id=gadget_id,
        size=size,
        color=color,
        model=model,
        variant_type=variant_type,
        sku=sku,
        price_modifier=price_modifier or 0.0,
        image_path=image_path
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    log_action(
        db=db,
        action_type="CREATE_GADGET_VARIANT",
        entity_type="GADGET_VARIANT",
        entity_id=variant.id,
        performed_by=performed_by,
        details=f"Created variant (SKU: {variant.sku}) for gadget '{gadget.name}'"
    )
    db.commit()
    return variant

def delete_gadget(db: Session, gadget_id: int, performed_by: int) -> bool:
    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    # Check total stock across all variants
    total_stock = sum(v.stock_quantity for v in gadget.variants)
    if total_stock > 0:
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

    db.commit()
    db.refresh(gadget)

    log_action(
        db=db,
        action_type="UPDATE_GADGET",
        entity_type="GADGET",
        entity_id=gadget.id,
        performed_by=performed_by,
        details=f"Updated gadget '{gadget.name}' (Category: {gadget.category})"
    )
    db.commit()
    return gadget


def update_gadget_variants(
    db: Session,
    gadget_id: int,
    variants_data: list,
    performed_by: int
) -> list:
    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    existing_variants = db.query(GadgetVariant).filter_by(gadget_id=gadget_id).all()
    existing_by_id = {v.id: v for v in existing_variants}

    updated_list = []
    
    for v_data in variants_data:
        v_id = v_data.get("id")
        if v_id and v_id in existing_by_id:
            # Update existing
            v = existing_by_id[v_id]
            v.size = v_data.get("size")
            v.color = v_data.get("color")
            v.model = v_data.get("model")
            v.variant_type = v_data.get("variant_type")
            v.sku = v_data.get("sku")
            v.price_modifier = v_data.get("price_modifier") or 0.0
            v.image_path = v_data.get("image_path")
            
            # Remove from tracking dict so it doesn't get deleted
            existing_by_id.pop(v_id)
            updated_list.append(v)
            
            log_action(
                db=db,
                action_type="UPDATE_GADGET_VARIANT",
                entity_type="GADGET_VARIANT",
                entity_id=v.id,
                performed_by=performed_by,
                details=f"Updated variant (SKU: {v.sku}) for gadget '{gadget.name}'"
            )
        else:
            # Create new
            v = GadgetVariant(
                gadget_id=gadget_id,
                size=v_data.get("size"),
                color=v_data.get("color"),
                model=v_data.get("model"),
                variant_type=v_data.get("variant_type"),
                sku=v_data.get("sku"),
                price_modifier=v_data.get("price_modifier") or 0.0,
                image_path=v_data.get("image_path")
            )
            db.add(v)
            db.flush() # Flush to generate id
            updated_list.append(v)
            
            log_action(
                db=db,
                action_type="CREATE_GADGET_VARIANT",
                entity_type="GADGET_VARIANT",
                entity_id=v.id,
                performed_by=performed_by,
                details=f"Created variant (SKU: {v.sku}) for gadget '{gadget.name}'"
            )

    # Delete remaining variants that were not in the payload
    for v_id, v in existing_by_id.items():
        # Validation: do not allow deletion of variants with stock_quantity > 0
        if v.stock_quantity > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Impossibile eliminare la variante SKU {v.sku} perché ha ancora {v.stock_quantity} pezzi in magazzino."
            )
            
        db.delete(v)
        log_action(
            db=db,
            action_type="DELETE_GADGET_VARIANT",
            entity_type="GADGET_VARIANT",
            entity_id=v_id,
            performed_by=performed_by,
            details=f"Deleted variant (SKU: {v.sku}) for gadget '{gadget.name}'"
        )

    db.commit()
    return updated_list
def create_stock_movement(
    db: Session,
    variant_id: int,
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

    variant = db.query(GadgetVariant).get(variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

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
            variant_id=variant_id, warehouse_id=from_warehouse_id
        ).first()
        if not stock_from or stock_from.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock in source warehouse")
        stock_from.quantity -= quantity

    # 2. Add stock to destination warehouse
    if to_warehouse_id:
        stock_to = db.query(GadgetVariantStock).filter_by(
            variant_id=variant_id, warehouse_id=to_warehouse_id
        ).first()
        if not stock_to:
            stock_to = GadgetVariantStock(
                variant_id=variant_id,
                warehouse_id=to_warehouse_id,
                quantity=0
            )
            db.add(stock_to)
        stock_to.quantity += quantity

    # 3. Create movement log
    movement = StockMovement(
        variant_id=variant_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        quantity=quantity,
        movement_type=movement_type,
        performed_by=performed_by,
        notes=notes
    )
    db.add(movement)
    db.flush()

    # 4. Update total aggregated stock on variant
    total_stock = db.query(func.sum(GadgetVariantStock.quantity)).filter_by(variant_id=variant.id).scalar() or 0
    variant.stock_quantity = total_stock

    db.commit()

    log_action(
        db=db,
        action_type="STOCK_MOVEMENT",
        entity_type="STOCK_MOVEMENT",
        entity_id=movement.id,
        performed_by=performed_by,
        details=f"Stock movement: {movement_type} (Quantity: {quantity}) for SKU {variant.sku or variant.id}"
    )
    db.commit()
    return movement
