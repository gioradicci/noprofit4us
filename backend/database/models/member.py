from sqlalchemy import Column, Integer, ForeignKey
from database.base import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    membership_number = Column(Integer, unique=True)

    

