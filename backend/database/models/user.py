from sqlalchemy import Column, Integer, String, Boolean, Date
from database.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    auth0_id = Column(String, unique=True)
    email = Column(String, nullable=True)

    password_hash = Column(String, nullable=True)
    google_id = Column(String, nullable=True)

    first_name = Column(String)
    last_name = Column(String)
    tax_code = Column(String, unique=True)

    birth_date = Column(Date)
    birth_place = Column(String)

    document_type = Column(String)
    document_number = Column(String)
    document_expiry = Column(Date)

    phone = Column(String)
    address = Column(String)
    city = Column(String)
    zip_code = Column(String)
    province = Column(String)
    municipality = Column(String)
    municipio_roma = Column(String)

    profession = Column(String)
    usage_type = Column(String)
    avg_km_per_day = Column(Integer)

    member_type = Column(String)
    payment_method = Column(String)
    

    # workflow
    status = Column(String, default="PENDING")  
    # PENDING / APPROVED / REJECTED

    role = Column(String, default="USER")
    # USER, MEMBER, TREASURER, ADMIN, 
    is_active = Column(Boolean, default=True)



    status = Column(String, default="INCOMPLETE")
    # INCOMPLETE → appena login Google
    # PENDING → ha compilato profilo
    # APPROVED → approvato
    # REJECTED 
    # EXPIRED
