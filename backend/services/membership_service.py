from datetime import date

from sqlalchemy.orm import Session

from database.models.member import Member
from database.models.membership import Membership
from database.models.user import User
from domain.services.membership_domain import calculate_membership_periods


# Serve a gestire il progressivo
def generate_membership_number(db: Session):

    last_member = db.query(Member).order_by(Member.membership_number.desc()).first()

    if not last_member:
        return 1

    return last_member.membership_number + 1


def generate_card_number_for_year(db: Session, reference_year: int) -> int:

    # Modifica per evitare di far camminare troppi dati in rete
    last_membership = (
        db.query(Membership)
        .filter(Membership.reference_year == reference_year)
        .order_by(Membership.card_number.desc())
        .first()
    )
    if not last_membership or not last_membership.card_number:
        return 1
    return last_membership.card_number + 1


def create_membership(member: Member, user: User, db: Session, is_renewal=False):
    """Create the membership card(s) for a new enrollment or a renewal.

    Outside the early-renewal window a single card for the current year is issued.
    From November a second card for the following year is issued as well: it is
    already paid but not yet valid (its ``start_date`` is 01/01 of the next year),
    so it is shown as a grey/inactive card on the member Home.
    """
    today = date.today()
    amount = 30 if user.member_type == "SOSTENITORE" else 10

    memberships = []

    for index, (start_date, end_date, reference_year) in enumerate(
        calculate_membership_periods(today)
    ):
        membership = Membership(
            member_id=member.id,
            start_date=start_date,
            end_date=end_date,
            reference_year=reference_year,
            card_number=generate_card_number_for_year(db, reference_year),
            payment_date=today,
            amount=amount,
            payment_method=user.payment_method,
            is_paid=True,
            # The current-year card inherits the passed flag; any additional
            # (next-year) card is by definition a renewal.
            is_renewal=is_renewal or index > 0,
        )
        db.add(membership)
        memberships.append(membership)

    return memberships
