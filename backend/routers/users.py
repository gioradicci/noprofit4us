from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from pydantic import BaseModel, validator
from typing import Optional, List
import re
import openpyxl
from io import BytesIO


from database.database import get_db
from database.models.user import User
from database.models.member import Member
from database.models.membership import Membership
from database.models.audit import AuditLog


from dependencies.auth import get_current_user
from services.user_service import approve_user
from services.audit_service import log_action

from domain.services.membership_domain import (
    calculate_membership_period,
    calculate_reference_year
)

#router = APIRouter(prefix="/users")
router = APIRouter()


# Pydantic validation schemas
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tax_code: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    payment_method: Optional[str] = None
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    document_expiry: Optional[date] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    province: Optional[str] = None
    municipality: Optional[str] = None
    profession: Optional[str] = None
    usage_type: Optional[List[str]] = None
    avg_km_per_day: Optional[int] = None
    member_type: Optional[str] = None
    municipio_roma: Optional[str] = None

    @validator("tax_code")
    def validate_tax_code(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if not v:
            return None
        cf_pattern = r'^([A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z0-9]{4})[A-Z0-9]{1}$'
        piva_pattern = r'^\d{11}$'
        if not (re.match(cf_pattern, v) or re.match(piva_pattern, v)):
            raise ValueError("Codice Fiscale o Partita IVA non valido")
        return v


# Entity serialization helpers
def serialize_user(user: User, db: Session) -> dict:
    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    
    if user_dict.get("birth_date") and not isinstance(user_dict["birth_date"], str):
        user_dict["birth_date"] = user_dict["birth_date"].isoformat()
    if user_dict.get("document_expiry") and not isinstance(user_dict["document_expiry"], str):
        user_dict["document_expiry"] = user_dict["document_expiry"].isoformat()

    if user_dict.get("usage_type"):
        user_dict["usage_type"] = [u.strip() for u in user_dict["usage_type"].split(",") if u.strip()]
    else:
        user_dict["usage_type"] = []
        
    user_dict["roles"] = getattr(user, "roles", [])
    
    # Initialize membership placeholders
    user_dict["membership_number"] = None
    user_dict["start_date"] = None
    user_dict["end_date"] = None
    user_dict["is_paid"] = False
    user_dict["reference_year"] = None
    user_dict["is_renewal_pending"] = False
    user_dict["has_active_membership"] = False

    # Fetch member details if present
    member = db.query(Member).filter_by(user_id=user.id).first()
    if member:
        memberships = db.query(Membership).filter_by(member_id=member.id).order_by(Membership.end_date.desc()).all()
        if memberships:
            active_membership = next((m for m in memberships if m.is_paid and m.end_date >= date.today()), None)
            pending_renewal = next((m for m in memberships if not m.is_paid and m.is_renewal), None)

            if active_membership:
                user_dict["has_active_membership"] = True

            membership = active_membership if active_membership else memberships[0]

            user_dict["membership_number"] = membership.card_number
            user_dict["start_date"] = membership.start_date.isoformat() if membership.start_date else None
            user_dict["end_date"] = membership.end_date.isoformat() if membership.end_date else None
            user_dict["is_paid"] = membership.is_paid
            user_dict["reference_year"] = membership.reference_year
            
            user_dict["is_renewal_pending"] = pending_renewal is not None
            if pending_renewal:
                user_dict["pending_renewal_year"] = pending_renewal.reference_year
        else:
            user_dict["membership_number"] = member.membership_number

    return user_dict


def serialize_membership(membership: Membership) -> dict:
    return {
        "id": membership.id,
        "member_id": membership.member_id,
        "start_date": membership.start_date.isoformat() if membership.start_date else None,
        "end_date": membership.end_date.isoformat() if membership.end_date else None,
        "reference_year": membership.reference_year,
        "card_number": membership.card_number,
        "amount": membership.amount,
        "payment_method": membership.payment_method,
        "is_paid": membership.is_paid,
        "payment_date": membership.payment_date.isoformat() if membership.payment_date else None,
        "is_renewal": membership.is_renewal
    }


@router.get("/me")
def me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Log authentication event if not logged in the last 15 minutes
    recent_login = db.query(AuditLog).filter(
        AuditLog.action_type == "LOGIN",
        AuditLog.performed_by == current_user.id,
        AuditLog.timestamp >= datetime.utcnow() - timedelta(minutes=15)
    ).first()
    
    if not recent_login:
        log_action(
            db=db,
            action_type="LOGIN",
            entity_type="USER",
            entity_id=current_user.id,
            performed_by=current_user.id,
            details=f"User {current_user.id} authenticated into the system"
        )
        db.commit()

    return serialize_user(current_user, db)


@router.put("/me")
def update_me(
    payload: UserUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    changed_fields = []
    is_submitting_candidacy = False

    # Extract update fields sent by client
    update_data = payload.dict(exclude_unset=True)

    for key, value in update_data.items():
        original_val = getattr(user, key)
        parsed_value = value
        
        # Special handling for usage_type since it's stored as comma-separated string in DB
        if key == "usage_type" and isinstance(value, list):
            parsed_value = ",".join(value) if value else None
            
        if original_val != parsed_value:
            changed_fields.append(key)
            setattr(user, key, parsed_value)

    # State transition logic
    if user.first_name and user.last_name and user.tax_code and user.status == "INCOMPLETE":
        user.status = "PENDING"
        is_submitting_candidacy = True

    from sqlalchemy.exc import IntegrityError
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if "tax_code" in str(e).lower():
            raise HTTPException(status_code=400, detail="Il Codice Fiscale inserito è già registrato da un altro utente.")
        raise HTTPException(status_code=400, detail="Errore durante il salvataggio dei dati nel database.")
    db.refresh(user)

    if changed_fields:
        log_action(
            db=db,
            action_type="UPDATE_PROFILE",
            entity_type="USER",
            entity_id=user.id,
            performed_by=user.id,
            details=f"User updated fields: {', '.join(changed_fields)}"
        )
    
    if is_submitting_candidacy:
        log_action(
            db=db,
            action_type="SUBMIT_CANDIDACY",
            entity_type="USER",
            entity_id=user.id,
            performed_by=user.id,
            details="User submitted registration candidacy"
        )
        
    if changed_fields or is_submitting_candidacy:
        db.commit()

    return serialize_user(user, db)
class RenewRequest(BaseModel):
    payment_method: str
    member_type: str

@router.post("/me/request-renew")
def request_renew(
    payload: RenewRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = db.query(Member).filter_by(user_id=current_user.id).first()
    if not member:
        raise HTTPException(status_code=400, detail="Not a member yet")

    latest_membership = db.query(Membership).filter_by(member_id=member.id).order_by(Membership.end_date.desc()).first()
    if latest_membership and not latest_membership.is_paid:
        raise HTTPException(status_code=400, detail="Renewal already pending")

    # Update payment method and member type
    current_user.payment_method = payload.payment_method
    current_user.member_type = payload.member_type
    db.commit()

    today = date.today()
    if latest_membership and latest_membership.end_date >= today:
        ref_year = latest_membership.end_date.year + 1
        start = date(ref_year, 1, 1)
        end = date(ref_year, 12, 31)
    else:
        start, end = calculate_membership_period(today)
        ref_year = calculate_reference_year(today)

    new_membership = Membership(
        member_id=member.id,
        start_date=start,
        end_date=end,
        reference_year=ref_year,
        card_number=None, # Non ancora assegnato
        amount=30 if payload.member_type == "SOSTENITORE" else 10,
        payment_method=payload.payment_method,
        is_paid=False,
        is_renewal=True
    )
    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    log_action(
        db=db,
        action_type="SUBMIT_CANDIDACY",
        entity_type="MEMBERSHIP",
        entity_id=new_membership.id,
        performed_by=current_user.id,
        details=f"User submitted renewal candidacy for year {ref_year}"
    )
    db.commit()

    return serialize_membership(new_membership)
@router.get("/dashboard")
def dashboard(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ SOLO ADMIN o TREASURER
    roles = current_user.roles

    if "ADMIN" not in roles and "TREASURER" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")


    today = date.today()

    users = db.query(User).all()

    result = []

    for u in users:

        # ✅ 1. recupera MEMBER
        member = db.query(Member).filter(Member.user_id == u.id).first()

        latest_membership = None

        # ✅ 2. recupera ultima MEMBERSHIP
        if member:
            latest_membership = db.query(Membership) \
                .filter(Membership.member_id == member.id) \
                .order_by(Membership.end_date.desc()) \
                .first()

        membership_status = "NONE"
        membership_end = None

        # ✅ UTENTE IN ATTESA
        if u.status == "PENDING":
            membership_status = "PENDING"

        # ✅ UTENTE CON MEMBERSHIP
        elif latest_membership:
            membership_end = latest_membership.end_date

            if not latest_membership.is_paid:
                membership_status = "RENEWAL_PENDING"
            elif latest_membership.end_date >= today:
                membership_status = "ACTIVE"
            else:
                membership_status = "EXPIRED"

        # ✅ UTENTE NON COMPLETO
        elif u.status == "INCOMPLETE":
            membership_status = "INCOMPLETE"

        result.append({
            "id": u.id,
            "card_number" : latest_membership.card_number if latest_membership else "NA",
            "auth0_id": u.auth0_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "status": u.status,
            "membership_status": membership_status,
            "membership_end": membership_end
        })

    return result


@router.get("/export")
def export_users(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ SOLO ADMIN o TREASURER
    roles = current_user.roles

    if "ADMIN" not in roles and "TREASURER" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    today = date.today()
    users = db.query(User).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Utenti"

    headers_row = [
        "ID", "Nome", "Cognome", "Email", "Codice Fiscale", 
        "Telefono", "Indirizzo", "Citta", "Provincia", "CAP",
        "Stato Profilo", "Stato Membership", "Scadenza Membership"
    ]
    ws.append(headers_row)

    for u in users:
        member = db.query(Member).filter(Member.user_id == u.id).first()
        latest_membership = None
        if member:
            latest_membership = db.query(Membership) \
                .filter(Membership.member_id == member.id) \
                .order_by(Membership.end_date.desc()) \
                .first()

        membership_status = "NONE"
        membership_end = ""

        if u.status == "PENDING":
            membership_status = "PENDING"
        elif latest_membership:
            membership_end = latest_membership.end_date.isoformat() if latest_membership.end_date else ""
            if not latest_membership.is_paid:
                membership_status = "RENEWAL_PENDING"
            elif latest_membership.end_date >= today:
                membership_status = "ACTIVE"
            else:
                membership_status = "EXPIRED"
        elif u.status == "INCOMPLETE":
            membership_status = "INCOMPLETE"

        ws.append([
            u.id,
            u.first_name or "",
            u.last_name or "",
            u.email or "",
            u.tax_code or "",
            u.phone or "",
            u.address or "",
            u.city or "",
            u.province or "",
            u.zip_code or "",
            u.status or "",
            membership_status,
            membership_end
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="utenti.xlsx"'
    }
    return StreamingResponse(iter([output.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


#  LISTA UTENTI (solo ADMIN)
@router.get("/")
def get_users(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "ADMIN" and user.role != "TREASURER":
        raise HTTPException(status_code=403, detail="Forbidden: Only ADMIN can see users")

    users = db.query(User).all()
    return [serialize_user(u, db) for u in users]


# RIFIUTA UTENTE
@router.put("/{id}/reject")
def reject_user(
    id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role != "TREASURER":
        raise HTTPException(status_code=403, detail="Only treasurer can reject")

    target = db.query(User).get(id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.status != "PENDING":
        raise HTTPException(status_code=400, detail="Already processed")

    target.status = "REJECTED"
    db.commit()

    return {"status": "rejected"}


# CONFERMA RINNOVO (APPROVA LA MEMBERSHIP PENDENTE)
@router.post("/{id}/renew")
@router.put("/{id}/renew")
def renew_member(
    id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role != "TREASURER" and "TREASURER" not in user.roles and "ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Only treasurer or admin can renew")

    member = db.query(Member).filter(Member.user_id == id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    pending_membership = db.query(Membership).filter(
        Membership.member_id == member.id,
        Membership.is_paid == False,
        Membership.is_renewal == True
    ).order_by(Membership.id.desc()).first()

    if not pending_membership:
        raise HTTPException(status_code=404, detail="No pending renewal request found")
        
    from services.membership_service import generate_card_number_for_year
    pending_membership.is_paid = True
    pending_membership.payment_date = date.today()
    pending_membership.card_number = generate_card_number_for_year(db, pending_membership.reference_year)
    
    log_action(
        db=db,
        action_type="APPROVE_RENEWAL",
        entity_type="MEMBERSHIP",
        entity_id=pending_membership.id,
        performed_by=user.id,
        details=f"Admin/Treasurer approved renewal for member {member.id}, membership ID {pending_membership.id}"
    )

    db.commit()
    db.refresh(pending_membership)

    return serialize_membership(pending_membership)


# DETTAGLIO UTENTE (self o admin/treasurer)
@router.get("/{id}")
def get_user(
    id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target = db.query(User).get(id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # solo se stesso, a meno che non sia ADMIN o TREASURER
    if user.role not in ["ADMIN", "TREASURER"] and user.id != id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return serialize_user(target, db)


@router.put("/{id}/pay")
def register_payment(
    id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles = current_user.roles
    if "TREASURER" not in roles and "ADMIN" not in roles:
        raise HTTPException(403)

    user = db.query(User).get(id)
    if not user:
        raise HTTPException(404, "User not found")

    user.status = "PAID"

    log_action(
        db=db,
        action_type="APPROVE_PAYMENT",
        entity_type="USER",
        entity_id=user.id,
        performed_by=current_user.id,
        details=f"Admin/Treasurer approved payment for user {user.id} (status set to PAID)"
    )

    db.commit()
    db.refresh(user)

    return serialize_user(user, db)


# PAGAMENTO E APPROVAZIONE SIMULTANEI (Transazionale e Atomico)
@router.put("/{id}/pay-and-approve")
def pay_and_approve(
    id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles = current_user.roles
    if "TREASURER" not in roles and "ADMIN" not in roles:
        raise HTTPException(403, "Not authorized")

    user = db.get(User, id)
    if not user:
        raise HTTPException(404, "User not found")

    if user.status != "PENDING":
        raise HTTPException(400, "User is not in PENDING status")

    try:
        user.status = "PAID"
        db.flush()

        log_action(
            db=db,
            action_type="APPROVE_PAYMENT",
            entity_type="USER",
            entity_id=user.id,
            performed_by=current_user.id,
            details=f"Admin/Treasurer approved payment for user {user.id} during pay-and-approve"
        )

        approved_user = approve_user(user, db, performed_by=current_user.id)
        return serialize_user(approved_user, db)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Errore durante l'approvazione: {str(e)}")

