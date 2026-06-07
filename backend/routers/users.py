from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta


from database.database import get_db
from database.models.user import User
from database.models.member import Member
from database.models.membership import Membership


from dependencies.auth import get_current_user
from services.user_service import approve_user

from domain.services.membership_domain import (
    calculate_membership_period,
    calculate_reference_year
)

router = APIRouter(prefix="/users")


@router.get("/me")
def me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Convert target SQLAlchemy model to dictionary
    user_dict = {c.name: getattr(current_user, c.name) for c in current_user.__table__.columns}
    
    # Format dates to string
    if user_dict.get("birth_date"):
        user_dict["birth_date"] = user_dict["birth_date"].isoformat()
    if user_dict.get("document_expiry"):
        user_dict["document_expiry"] = user_dict["document_expiry"].isoformat()
        
    user_dict["roles"] = getattr(current_user, "roles", [])
    
    # Initialize membership placeholders
    user_dict["membership_number"] = None
    user_dict["start_date"] = None
    user_dict["end_date"] = None
    user_dict["is_paid"] = False
    user_dict["reference_year"] = None

    # Fetch member details if present
    member = db.query(Member).filter_by(user_id=current_user.id).first()
    if member:
        user_dict["membership_number"] = member.membership_number
        membership = db.query(Membership).filter_by(member_id=member.id).order_by(Membership.end_date.desc()).first()
        if membership:
            user_dict["start_date"] = membership.start_date.isoformat() if membership.start_date else None
            user_dict["end_date"] = membership.end_date.isoformat() if membership.end_date else None
            user_dict["is_paid"] = membership.is_paid
            user_dict["reference_year"] = membership.reference_year

    return user_dict


@router.put("/me")
def update_me(
    payload: dict,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    allowed_fields = [
        "first_name",
        "last_name",
        "tax_code",
        "phone",
        "address",
        "document_type",
        "document_number",
        "payment_method"
    ]

    for key, value in payload.items():
        if key in allowed_fields:
            setattr(user, key, value)

    # ✅ logica stato
    if user.first_name and user.last_name and user.tax_code and user.status == "INCOMPLETE":
        user.status = "PENDING"

    db.commit()
    db.refresh(user)
    
    return user

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
            membership_end = latest_membersship_end = latest_membership.end_date

            if latest_membership.end_date >= today:
                membership_status = "ACTIVE"
            else:
                membership_status = "EXPIRED"

        # ✅ UTENTE NON COMPLETO
        elif u.status == "INCOMPLETE":
            membership_status = "INCOMPLETE"

        result.append({
            "id": u.id,
            "auth0_id": u.auth0_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "status": u.status,
            "membership_status": membership_status,
            "membership_end": membership_end
        })

    return result


#  LISTA UTENTI (solo ADMIN)
@router.get("/")
def get_users(user=Depends(get_current_user), db: Session = Depends(get_db)):

    if user.role != "ADMIN" and user.role != "TREASURER":
        raise HTTPException(status_code=403, detail="Forbidden: Only ADMIN can see users")

    return db.query(User).all()






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


# RINNOVO ISCRIZIONE (CREA NUOVA MEMBERSHIP)
@router.post("/{id}/renew")
def renew_member(
    id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if user.role != "TREASURER":
        raise HTTPException(status_code=403, detail="Only treasurer can renew")

    member = db.query(Member).get(id)

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    today = date.today()

    start, end = calculate_membership_period(today)

    membership = Membership(
        member_id=member.id,
        start_date=start,
        end_date=end,
        reference_year=calculate_reference_year(today),
        is_renewal=True
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


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

    # se MEMBER → solo se stesso
    if user.role == "MEMBER" and user.id != id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return target



@router.put("/{id}/pay")
def register_payment(
    id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles = current_user.roles

    if "TREASURER" not in roles and "ADMIN" not in roles:
        raise HTTPException(403)

    user = db.get(User, id)

    if not user:
        raise HTTPException(404, "User not found")

    # ✅ QUI VIENE SETTATO
    user.status = "PAID"

    db.commit()
    db.refresh(user)

    return user

    
# APPROVA UTENTE → CREA MEMBER + MEMBERSHIP
@router.put("/{id}/approve")
def approve(
    id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    roles = current_user.roles

    if "TREASURER" not in roles and "ADMIN" not in roles:
        raise HTTPException(403, "Only Treasurer")

    user = db.get(User, id)

    if not user:
        raise HTTPException(404, "User not found.")

    return approve_user(user, db)


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
        # 1. Imposta lo stato su PAID
        user.status = "PAID"
        db.flush()

        # 2. Approva l'utente (esegue commit e refresh internamente)
        approved_user = approve_user(user, db)
        return approved_user
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Errore durante l'approvazione: {str(e)}")

