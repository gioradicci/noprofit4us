from datetime import date
from database.models.user import User
from domain.services.membership_domain import calculate_membership_period
from services.audit_service import log_action
from sqlalchemy.orm import Session
from database.models.member import Member
from database.models.membership import Membership
from datetime import date


# #Serve a gestire il progressivo
def generate_membership_number(db: Session):


    last_member = db.query(Member).order_by(Member.membership_number.desc()).first()

    if not last_member:
        return 1

    return last_member.membership_number + 1


def generate_card_number_for_year(db: Session, reference_year: int) -> int:
    
    #Modifica per evitare di far camminare troppi dati in rete
    last_membership = db.query(Membership).filter(Membership.reference_year == reference_year).order_by(Membership.card_number.desc()).first()
    if not last_membership or not last_membership.card_number:
        return 1
    return last_membership.card_number + 1

    # last_membership = db.query(Membership).filter(Membership.reference_year == reference_year).order_by(Membership.card_number.desc()).first()
    # if not last_membership or not last_membership.card_number:
    #     return 1
    # return last_membership.card_number + 1


def create_membership(member: Member, user: User, db: Session, is_renewal=False):

    start_date, end_date = calculate_membership_period(date.today())
    ref_year = start_date.year

    membership = Membership(
        member_id=member.id,
        start_date=start_date,
        end_date=end_date,
        reference_year=ref_year,
        card_number=generate_card_number_for_year(db, ref_year),
        payment_date=date.today(),
        amount=30 if user.member_type == "SOSTENITORE" else 10,
        payment_method=user.payment_method,
        is_paid=True,
        is_renewal=is_renewal
    )

    db.add(membership)

    return membership

