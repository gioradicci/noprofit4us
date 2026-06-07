from sqlalchemy.orm import Session

from database.models.member import Member
from database.models.user import User
from services.membership_service import generate_membership_number


def get_or_create_member(user: User, db: Session):

    member = db.query(Member).filter_by(user_id=user.id).first()

    if not member:
        member = Member(
            user_id=user.id,
            membership_number=generate_membership_number(db)
        )
        db.add(member)
        db.flush()

    return member
