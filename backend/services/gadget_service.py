from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException
from typing import Optional
from database.models.gadget import Gadget, Warehouse, GadgetVariantStock, StockMovement, GadgetLock, GadgetLoan
from database.models.user import User
from services.audit_service import log_action
from datetime import datetime, timedelta


def _loan_remaining(loan: GadgetLoan) -> int:
    """Pezzi ancora in carico all'assegnatario (né rientrati né consegnati definitivamente)."""
    return loan.quantity - loan.returned_quantity - (loan.delivered_quantity or 0)


def _refresh_loan_status(loan: GadgetLoan) -> str:
    """Ricalcola lo stato dell'affidamento in base a rientri e consegne definitive.

    Stati possibili:
      - ACTIVE: nessun rientro/consegna, tutto ancora in carico
      - PARTIAL: definizione parziale (alcuni rientrati e/o consegnati, residuo > 0)
      - RETURNED: tutto rientrato a magazzino
      - DELIVERED: tutto consegnato definitivamente all'assegnatario
      - COMPLETED: definito in parte con rientro e in parte con consegna
    """
    delivered = loan.delivered_quantity or 0
    remaining = loan.quantity - loan.returned_quantity - delivered

    if remaining > 0:
        loan.status = "PARTIAL" if (loan.returned_quantity + delivered) > 0 else "ACTIVE"
    else:
        if delivered and loan.returned_quantity:
            loan.status = "COMPLETED"
        elif delivered:
            loan.status = "DELIVERED"
        else:
            loan.status = "RETURNED"
        if not loan.returned_date:
            loan.returned_date = datetime.utcnow()

    loan.updated_at = datetime.utcnow()
    return loan.status


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
        lock.expires_at = now + timedelta(minutes=2)
    else:
        # Create new lock
        lock = GadgetLock(
            gadget_id=gadget_id,
            user_id=user_id,
            locked_at=now,
            expires_at=now + timedelta(minutes=2)
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
    is_not_for_sale: Optional[bool] = None,
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
        is_not_for_sale = is_not_for_sale,
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

    active_loans = db.query(func.sum(
        GadgetLoan.quantity - GadgetLoan.returned_quantity - func.coalesce(GadgetLoan.delivered_quantity, 0)
    )).filter(
        GadgetLoan.gadget_id == gadget_id
    ).scalar() or 0
    if active_loans > 0:
        raise HTTPException(status_code=400, detail="Impossibile eliminare il gadget perché risultano ancora pezzi in affidamento.")

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
    is_not_for_sale: Optional[bool] = None,
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
    gadget.is_not_for_sale = is_not_for_sale

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
        # I gadget "non in vendita" (uso interno/staff) non possono essere consegnati.
        if gadget.is_not_for_sale:
            raise HTTPException(
                status_code=400,
                detail="I gadget contrassegnati come 'non in vendita' (uso interno) non possono essere consegnati."
            )

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


def create_gadget_loan(
    db: Session,
    gadget_id: int,
    from_warehouse_id: int,
    quantity: int,
    performed_by: int,
    assigned_to_user_id: Optional[int] = None,
    assigned_to_name: Optional[str] = None,
    expected_return_date: Optional[datetime] = None,
    notes: Optional[str] = None
) -> GadgetLoan:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="La quantità deve essere maggiore di zero")

    gadget = db.query(Gadget).get(gadget_id)
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget non trovato")

    wh = db.query(Warehouse).get(from_warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Magazzino di origine non trovato")

    # Verifica giacenza disponibile
    stock_from = db.query(GadgetVariantStock).filter_by(
        gadget_id=gadget_id, warehouse_id=from_warehouse_id
    ).first()
    if not stock_from or stock_from.quantity < quantity:
        raise HTTPException(status_code=400, detail="Giacenza insufficiente nel magazzino selezionato")

    # Nome assegnatario per note e visualizzazione
    assignee_display = (assigned_to_name or "").strip()
    if assigned_to_user_id:
        target_user = db.query(User).get(assigned_to_user_id)
        if target_user:
            u_name = f"{target_user.first_name or ''} {target_user.last_name or ''}".strip()
            assignee_display = u_name or target_user.email or f"Utente {assigned_to_user_id}"

    if not assignee_display:
        assignee_display = "Non specificato"

    # Scala dal magazzino
    stock_from.quantity -= quantity

    # Crea affidamento: il flush assegna l'id necessario a collegare il movimento.
    loan = GadgetLoan(
        gadget_id=gadget_id,
        from_warehouse_id=from_warehouse_id,
        assigned_to_user_id=assigned_to_user_id,
        assigned_to_name=assignee_display,
        quantity=quantity,
        returned_quantity=0,
        delivered_quantity=0,
        status="ACTIVE",
        loan_date=datetime.utcnow(),
        expected_return_date=expected_return_date,
        notes=notes,
        performed_by=performed_by
    )
    db.add(loan)
    db.flush()

    # Registra movimento collegato all'affidamento
    movement = StockMovement(
        gadget_id=gadget_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=None,
        quantity=quantity,
        movement_type="LOAN",
        loan_id=loan.id,
        performed_by=performed_by,
        notes=f"Affidamento temporaneo a {assignee_display}" + (f": {notes}" if notes else "")
    )
    db.add(movement)

    # Aggiorna giacenza a magazzino (esclude le quantità in affidamento)
    total_stock = db.query(func.sum(GadgetVariantStock.quantity)).filter_by(gadget_id=gadget.id).scalar() or 0
    gadget.stock_quantity = total_stock

    db.commit()

    log_action(
        db=db,
        action_type="GADGET_LOAN_CREATE",
        entity_type="GADGET_LOAN",
        entity_id=loan.id,
        performed_by=performed_by,
        details=f"Affidamento temporaneo di {quantity}x {gadget.name} a {assignee_display} da magazzino {wh.name}."
    )
    db.commit()
    db.refresh(loan)
    return loan


def return_gadget_loan(
    db: Session,
    loan_id: int,
    returned_quantity: int,
    to_warehouse_id: int,
    performed_by: int,
    notes: Optional[str] = None
) -> GadgetLoan:
    loan = db.query(GadgetLoan).get(loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Affidamento non trovato")

    remaining = _loan_remaining(loan)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Questo affidamento è già stato completamente definito")

    if returned_quantity <= 0:
        raise HTTPException(status_code=400, detail="La quantità da restituire deve essere maggiore di zero")

    if returned_quantity > remaining:
        raise HTTPException(status_code=400, detail=f"Quantità da restituire ({returned_quantity}) superiore al residuo in carico ({remaining})")

    wh_to = db.query(Warehouse).get(to_warehouse_id)
    if not wh_to:
        raise HTTPException(status_code=404, detail="Magazzino di destinazione non trovato")

    gadget = db.query(Gadget).get(loan.gadget_id)
    assignee = loan.assigned_to_name or "Assegnatario"

    # 1. Riconsegna a magazzino
    stock_to = db.query(GadgetVariantStock).filter_by(
        gadget_id=loan.gadget_id, warehouse_id=to_warehouse_id
    ).first()
    if not stock_to:
        stock_to = GadgetVariantStock(
            gadget_id=loan.gadget_id,
            warehouse_id=to_warehouse_id,
            quantity=0
        )
        db.add(stock_to)
    stock_to.quantity += returned_quantity

    movement_return = StockMovement(
        gadget_id=loan.gadget_id,
        from_warehouse_id=None,
        to_warehouse_id=to_warehouse_id,
        quantity=returned_quantity,
        movement_type="LOAN_RETURN",
        loan_id=loan.id,
        performed_by=performed_by,
        notes=f"Rientro da affidamento di {assignee} in {wh_to.name}" + (f": {notes}" if notes else "")
    )
    db.add(movement_return)

    # 2. Aggiorna lo stato del loan
    loan.returned_quantity += returned_quantity
    _refresh_loan_status(loan)
    db.flush()
    # Aggiorna giacenza a magazzino (esclude le quantità ancora in affidamento)
    if gadget:
        total_stock = db.query(func.sum(GadgetVariantStock.quantity)).filter_by(gadget_id=gadget.id).scalar() or 0
        gadget.stock_quantity = total_stock

    db.commit()

    log_action(
        db=db,
        action_type="GADGET_LOAN_RETURN",
        entity_type="GADGET_LOAN",
        entity_id=loan.id,
        performed_by=performed_by,
        details=f"Riconsegna affidamento #{loan.id}: {returned_quantity} rientrati in {wh_to.name}."
    )
    db.commit()
    db.refresh(loan)
    return loan


def deliver_gadget_loan(
    db: Session,
    loan_id: int,
    delivered_quantity: int,
    performed_by: int,
    notes: Optional[str] = None
) -> GadgetLoan:
    """Registra la consegna definitiva a un assegnatario di materiale ancora in affidamento.

    Simile una DELIVERY, ma la merce non proviene dal magazzino (era già
    stata scaricata al momento dell'affidamento): va quindi a ridurre il residuo in
    carico dell'affidamento e a tracciare il movimento con tipo ``LOAN_DELIVERY``.
    """
    loan = db.query(GadgetLoan).get(loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Affidamento non trovato")

    remaining = _loan_remaining(loan)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Questo affidamento è già stato completamente definito")

    if delivered_quantity <= 0:
        raise HTTPException(status_code=400, detail="La quantità da consegnare deve essere maggiore di zero")

    if delivered_quantity > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Quantità da consegnare ({delivered_quantity}) superiore al residuo in carico ({remaining})"
        )

    gadget = db.query(Gadget).get(loan.gadget_id)
    # I gadget "non in vendita" (uso interno/staff) non possono essere consegnati
    # definitivamente all'assegnatario, anche se già in affidamento temporaneo.
    if gadget is not None and gadget.is_not_for_sale:
        raise HTTPException(
            status_code=400,
            detail="I gadget contrassegnati come 'non in vendita' (uso interno) non possono essere consegnati."
        )
    assignee = loan.assigned_to_name or "Assegnatario"

    # Registra il movimento: la merce esce dall'affidamento ed è conseguente all'assegnatario.
    movement = StockMovement(
        gadget_id=loan.gadget_id,
        from_warehouse_id=loan.from_warehouse_id,
        to_warehouse_id=None,
        quantity=delivered_quantity,
        movement_type="LOAN_DELIVERY",
        loan_id=loan.id,
        performed_by=performed_by,
        notes=f"Consegna definitiva di {assignee} per materiale in affidamento" + (f": {notes}" if notes else "")
    )
    db.add(movement)

    # Aggiorna l'affidamento e lo stato
    loan.delivered_quantity = (loan.delivered_quantity or 0) + delivered_quantity
    _refresh_loan_status(loan)
    db.flush()

    db.commit()

    log_action(
        db=db,
        action_type="GADGET_LOAN_DELIVER",
        entity_type="GADGET_LOAN",
        entity_id=loan.id,
        performed_by=performed_by,
        details=f"Consegna definitiva affidamento #{loan.id}: {delivered_quantity}x {gadget.name if gadget else ''} a {assignee}."
    )
    db.commit()
    db.refresh(loan)
    return loan


# ---------------------------------------------------------------------------
# Timeline movimentazioni per singolo gadget
# ---------------------------------------------------------------------------

def _serialize_warehouse(warehouse) -> Optional[dict]:
    if not warehouse:
        return None
    return {
        "id": warehouse.id,
        "name": warehouse.name,
        "code": warehouse.code,
    }


def _serialize_user(user) -> Optional[dict]:
    if not user:
        return None
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return {
        "id": user.id,
        "name": full_name or None,
        "email": user.email,
    }


def _movement_balance_delta(movement_type: str, quantity: int) -> int:
    """Variazione della giacenza fisica di magazzino prodotta dal movimento.

    - RESTOCK: entra in magazzino (+)
    - DELIVERY: esce definitivamente (-)
    - LOAN: esce dal magazzino verso l'assegnatario (-)
    - LOAN_RETURN: rientra in magazzino (+)
    - TRANSFER: spostamento interno, saldo totale invariato (0)
    - LOAN_DELIVERY: la merce era già uscita al momento del LOAN (0)
    """
    if movement_type == "RESTOCK":
        return quantity
    if movement_type in ("DELIVERY", "LOAN"):
        return -quantity
    if movement_type == "LOAN_RETURN":
        return quantity
    return 0


def _serialize_loan(loan: GadgetLoan) -> dict:
    remaining = _loan_remaining(loan)
    return {
        "id": loan.id,
        "assigned_to_user_id": loan.assigned_to_user_id,
        "assigned_to_name": loan.assigned_to_name,
        "quantity": loan.quantity,
        "returned_quantity": loan.returned_quantity or 0,
        "delivered_quantity": loan.delivered_quantity or 0,
        "remaining_quantity": remaining,
        "status": loan.status,
        "loan_date": loan.loan_date.isoformat() if loan.loan_date else None,
        "expected_return_date": loan.expected_return_date.isoformat() if loan.expected_return_date else None,
        "returned_date": loan.returned_date.isoformat() if loan.returned_date else None,
        "from_warehouse": _serialize_warehouse(loan.from_warehouse),
        "notes": loan.notes,
        "is_open": remaining > 0,
    }


def _serialize_movement_event(movement: StockMovement, loan_link_source: Optional[str] = None) -> dict:
    return {
        "id": f"movement-{movement.id}",
        "movement_id": movement.id,
        "movement_type": movement.movement_type,
        "timestamp": movement.timestamp.isoformat() if movement.timestamp else None,
        "quantity": movement.quantity,
        "delta": _movement_balance_delta(movement.movement_type, movement.quantity),
        "balance_after": None,
        "from_warehouse": _serialize_warehouse(movement.from_warehouse),
        "to_warehouse": _serialize_warehouse(movement.to_warehouse),
        "notes": movement.notes,
        "performer": _serialize_user(movement.performer),
        "loan_id": movement.loan_id,
        "loan_link_source": loan_link_source,
        "loan": None,
        "children": [],
    }


def _notes_mention_assignee(movement: StockMovement, loan: GadgetLoan) -> bool:
    """Fallback per i movimenti storici: l'assegnatario è citato nelle note."""
    name = (loan.assigned_to_name or "").strip().lower()
    if not name or name == "non specificato":
        return True
    notes = (movement.notes or "").lower()
    return name in notes


def _heuristic_capacity_available(movement: StockMovement, loan: GadgetLoan, used: dict) -> bool:
    if movement.movement_type == "LOAN_RETURN":
        capacity = loan.returned_quantity or 0
    elif movement.movement_type == "LOAN_DELIVERY":
        capacity = loan.delivered_quantity or 0
    else:
        return True
    key = (loan.id, movement.movement_type)
    return used.get(key, 0) + movement.quantity <= capacity


def _match_legacy_loan(
    movement: StockMovement,
    candidate_loans: list,
    used: Optional[dict] = None
    ) -> Optional[GadgetLoan]:
    """Ricostruisce il legame per i movimenti privi di loan_id.

    Usa nome assegnatario nelle note, data dell'affidamento e, per i LOAN,
    la quantità. È solo un fallback: i nuovi movimenti hanno sempre loan_id.
    """
    used = used or {}
    candidates = []
    for loan in candidate_loans:
        if loan.loan_date and movement.timestamp and loan.loan_date > movement.timestamp:
            continue
        if not _notes_mention_assignee(movement, loan):
            continue
        if movement.movement_type == "LOAN" and loan.quantity != movement.quantity:
            continue
        if movement.movement_type in ("LOAN_RETURN", "LOAN_DELIVERY"):
            if not _heuristic_capacity_available(movement, loan, used):
                continue
        candidates.append(loan)

    if not candidates:
        return None

    if movement.movement_type == "LOAN":
        reference = movement.timestamp or datetime.utcnow()
        candidates.sort(
            key=lambda loan: (
                abs(((loan.loan_date or reference) - reference).total_seconds()),
                loan.id,
            )
        )
    else:
        candidates.sort(key=lambda loan: (loan.loan_date or datetime.min, loan.id))
    return candidates[0]


def get_gadget_timeline(db: Session, gadget_id: int) -> dict:
    """Timeline cronologica delle movimentazioni di un gadget.

    Restituisce gli eventi in ordine crescente (dal primo restock in poi), con
    il saldo di magazzino dopo ogni evento. I movimenti LOAN diventano rami
    annidati che contengono le relative LOAN_RETURN / LOAN_DELIVERY.
    """
    gadget = (
        db.query(Gadget)
        .options(joinedload(Gadget.stocks).joinedload(GadgetVariantStock.warehouse))
        .filter(Gadget.id == gadget_id)
        .first()
    )
    if not gadget:
        raise HTTPException(status_code=404, detail="Gadget not found")

    movements = (
        db.query(StockMovement)
        .options(
            joinedload(StockMovement.from_warehouse),
            joinedload(StockMovement.to_warehouse),
            joinedload(StockMovement.performer),
        )
        .filter(StockMovement.gadget_id == gadget_id)
        .order_by(StockMovement.timestamp.asc(), StockMovement.id.asc())
        .all()
    )

    loans = (
        db.query(GadgetLoan)
        .options(
            joinedload(GadgetLoan.from_warehouse),
            joinedload(GadgetLoan.assigned_user),
        )
        .filter(GadgetLoan.gadget_id == gadget_id)
        .order_by(GadgetLoan.loan_date.asc(), GadgetLoan.id.asc())
        .all()
    )

    loans_by_id = {loan.id: loan for loan in loans}
    branch_events = {}
    standalone_events = []
    linked_loan_ids = set()
    heuristic_used = {}

    for movement in movements:
        if movement.movement_type == "LOAN":
            loan = None
            source = "none"
            if movement.loan_id and movement.loan_id in loans_by_id:
                loan = loans_by_id[movement.loan_id]
                source = "exact"
            else:
                loan = _match_legacy_loan(
                    movement,
                    [candidate for candidate in loans if candidate.id not in linked_loan_ids],
                    heuristic_used,
                )
                source = "heuristic" if loan else "none"

            event = _serialize_movement_event(movement, source)
            if loan:
                event["loan_id"] = loan.id
                event["loan"] = _serialize_loan(loan)
                branch_events[loan.id] = event
                linked_loan_ids.add(loan.id)
            else:
                standalone_events.append(event)
            continue

        if movement.movement_type in ("LOAN_RETURN", "LOAN_DELIVERY"):
            loan = None
            source = "none"
            if movement.loan_id and movement.loan_id in branch_events:
                loan = loans_by_id.get(movement.loan_id)
                source = "exact"
            else:
                loan = _match_legacy_loan(movement, loans, heuristic_used)
                source = "heuristic" if loan else "none"

            event = _serialize_movement_event(movement, source)
            if loan and loan.id in branch_events:
                event["loan_id"] = loan.id
                branch_events[loan.id]["children"].append(event)
                key = (loan.id, movement.movement_type)
                heuristic_used[key] = heuristic_used.get(key, 0) + movement.quantity
            else:
                standalone_events.append(event)
            continue

        standalone_events.append(_serialize_movement_event(movement))

    # Saldo progressivo calcolato su tutti i movimenti reali in ordine cronologico.
    balance_by_movement_id = {}
    running_balance = 0
    for movement in movements:
        running_balance += _movement_balance_delta(movement.movement_type, movement.quantity)
        balance_by_movement_id[movement.id] = running_balance

    def apply_balance(event: dict):
        movement_id = event.get("movement_id")
        if movement_id is not None:
            event["balance_after"] = balance_by_movement_id.get(movement_id)
        for child in event.get("children", []):
            child["balance_after"] = balance_by_movement_id.get(child.get("movement_id"))

    events = list(branch_events.values()) + standalone_events
    for event in events:
        apply_balance(event)

    # I figli degli affidamenti restano annidati: la lista top-level contiene
    # solo eventi radice, ordinati cronologicamente.
    events.sort(key=lambda event: (event.get("timestamp") or "", event.get("movement_id") or 0))
    for index, event in enumerate(events, start=1):
        event["sequence"] = index

    totals = {}
    for movement in movements:
        totals[movement.movement_type] = totals.get(movement.movement_type, 0) + movement.quantity

    restocked = totals.get("RESTOCK", 0)
    delivered = totals.get("DELIVERY", 0)
    loaned = totals.get("LOAN", 0)
    loan_returns = totals.get("LOAN_RETURN", 0)
    loan_deliveries = totals.get("LOAN_DELIVERY", 0)

    open_loans = [loan for loan in loans if _loan_remaining(loan) > 0]
    gadget_stock = gadget.stock_quantity or 0

    stock_by_warehouse = [
        {
            "warehouse_id": stock.warehouse_id,
            "warehouse_name": stock.warehouse.name if stock.warehouse else None,
            "warehouse_code": stock.warehouse.code if stock.warehouse else None,
            "quantity": stock.quantity or 0,
        }
        for stock in gadget.stocks
    ]
    stock_by_warehouse.sort(key=lambda item: (item["warehouse_name"] or "").lower())

    first_restock = next(
        (movement for movement in movements if movement.movement_type == "RESTOCK"),
        None,
    )
    first_event = movements[0] if movements else None
    last_event = movements[-1] if movements else None

    summary = {
        "total_restocked": restocked,
        "total_delivered": delivered,
        "total_loaned": loaned,
        "total_loan_returns": loan_returns,
        "total_loan_deliveries": loan_deliveries,
        "total_in": restocked + loan_returns,
        "total_out": delivered + loaned + loan_deliveries,
        "current_stock": running_balance,
        "gadget_stock_quantity": gadget_stock,
        "open_loans_remaining": sum(_loan_remaining(loan) for loan in open_loans),
        "open_loans_count": len(open_loans),
        "loans_count": len(loans),
        "unlinked_loans_count": len([loan for loan in loans if loan.id not in linked_loan_ids]),
        "movements_count": len(movements),
        "first_restock_at": first_restock.timestamp.isoformat() if first_restock and first_restock.timestamp else None,
        "first_event_at": first_event.timestamp.isoformat() if first_event and first_event.timestamp else None,
        "last_event_at": last_event.timestamp.isoformat() if last_event and last_event.timestamp else None,
        "is_reconciled": running_balance == gadget_stock,
        "stock_by_warehouse": stock_by_warehouse,
        "loans": [_serialize_loan(loan) for loan in loans],
    }

    return {
        "gadget": {
            "id": gadget.id,
            "name": gadget.name,
            "sku": gadget.sku,
            "category": gadget.category,
            "image_path": gadget.image_path,
            "size": gadget.size,
            "color": gadget.color,
            "model": gadget.model,
            "variant_type": gadget.variant_type,
            "is_not_for_sale": gadget.is_not_for_sale,
            "stock_quantity": gadget_stock,
            "created_at": gadget.created_at.isoformat() if gadget.created_at else None,
        },
        "summary": summary,
        "events": events,
    }
