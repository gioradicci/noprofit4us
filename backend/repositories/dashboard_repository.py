from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from database.models.membership import Membership
from database.models.user import User


def count_active_members(db: Session):
    today = date.today()

    return db.query(Membership).filter(
        Membership.is_paid == True,
        Membership.end_date >= today
    ).count()


def count_unpaid_memberships(db: Session):
    return db.query(Membership).filter(
        Membership.is_paid == False
    ).count()


def total_income(db: Session):
    return db.query(func.sum(Membership.amount)).scalar()


def count_pending_users(db: Session):
    return db.query(User).filter(
        User.status == "PENDING"
    ).count()


def count_renewals(db: Session):
    return db.query(Membership).filter(
        Membership.is_renewal == True
    ).count()