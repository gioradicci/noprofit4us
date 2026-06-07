from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    action_type = Column(String)      # es: APPROVE, PAYMENT
    entity_type = Column(String)      # es: MEMBERSHIP, USER
    entity_id = Column(Integer)

    performed_by = Column(Integer)

    timestamp = Column(DateTime, default=datetime.utcnow)

    details = Column(String)          # descrizione libera
