from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session
from database.models.member import Member
from database.models.membership import Membership
from database.models.user import User
from services.member_service import get_or_create_member
from services.membership_service import create_membership
from services.audit_service import log_action

# from domain.services.membership_domain import (
#     calculate_membership_period,
#     calculate_reference_year
# )



def approve_user(user: User, db: Session, performed_by: int = None):

    if user.status != "PAID":
        raise HTTPException(400, "User must be PAID before approval")

    #  1. crea o recupera Member
    member = get_or_create_member(user, db)

    #  2. crea Membership
    create_membership(member, user, db)

    #  3. aggiorna User
    user.status = "APPROVED"

    log_action(
        db=db,
        action_type="APPROVE_MEMBERSHIP",
        entity_type="USER",
        entity_id=user.id,
        performed_by=performed_by,
        details=f"Admin/Treasurer approved membership for user {user.id}"
    )

    db.commit()
    db.refresh(user)

    return user


