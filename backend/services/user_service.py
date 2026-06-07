from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session
from database.models.member import Member
from database.models.membership import Membership
from database.models.user import User
from services.member_service import get_or_create_member
from services.membership_service import create_membership

# from domain.services.membership_domain import (
#     calculate_membership_period,
#     calculate_reference_year
# )



def approve_user(user: User, db: Session):

    if user.status != "PAID":
        raise HTTPException(400, "User must be PAID before approval")

    #  1. crea o recupera Member
    member = get_or_create_member(user, db)

    # ✅ 2. crea Membership
    create_membership(member, user, db)

    # ✅ 3. aggiorna User
    user.status = "APPROVED"

    db.commit()
    db.refresh(user)

    return user



# def approve_user(user: User, db: Session):

#     # ✅ crea Member se non esiste
#     member = db.query(Member).filter_by(user_id=user.id).first()

#     if not member:
#         member = Member(
#             user_id=user.id,
#             membership_number=generate_membership_number(db)
#         )
#         db.add(member)
#         db.flush()

#     # ✅ uso dominio
#     start_date, end_date = calculate_membership_period(date.today())

#     membership = Membership(
#         member_id=member.id,
#         start_date=start_date,
#         end_date=end_date,
#         reference_year=start_date.year,
#         payment_date=date.today(),
#         amount=50,
#         payment_method=user.payment_method,
#         is_paid=True,
#         is_renewal=False
#     )

#     db.add(membership)

#     user.status = "APPROVED"

#     db.commit()
#     db.refresh(user)

#     return user
