from sqlalchemy import Column, Float, Integer, ForeignKey, Date, Boolean, String
from database.base import Base

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True)

    member_id = Column(Integer, ForeignKey("members.id"))

    start_date = Column(Date)
    end_date = Column(Date)

    reference_year = Column(Integer)
    card_number = Column(Integer, nullable=True)

    # pagamento
    payment_date = Column(Date, nullable=True)
    amount = Column(Integer, nullable=True) #10 per Ordinario, 30 per Sostenitore
    payment_method = Column(String, nullable=True)

    payment_amount = Column(Float)

    is_paid = Column(Boolean, default=False)

    is_renewal = Column(Boolean, default=False)