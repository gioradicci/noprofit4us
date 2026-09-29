from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base

class Gadget(Base):
    __tablename__ = "gadgets"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False)  # T-SHIRT, CAP, KEYCHAIN, PIN, STICKER, POSTER, OTHER
    min_donation = Column(Float, nullable=False)
    image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    size = Column(String, nullable=True)          # e.g. S, M, L, XL
    color = Column(String, nullable=True)         # e.g. Blu, Nero, Rosso
    model = Column(String, nullable=True)         # e.g. Uomo, Donna, Unisex
    variant_type = Column(String, nullable=True)  # e.g. Metallic, Glow-in-the-dark
    sku = Column(String, unique=True, nullable=True)
    stock_quantity = Column(Integer, default=0)    # Total aggregated stock
    is_not_for_sale = Column(Boolean, default=False, nullable=False) #Gadget or asset used internally but not for sale: 
            #is_not_for_sale =  TRUE : for staff/volunteers/internal use ONLY, FALSE : for sale

    stocks = relationship("GadgetVariantStock", back_populates="gadget", cascade="all, delete-orphan")
    movements = relationship("StockMovement", back_populates="gadget", cascade="all, delete-orphan")
    loans = relationship("GadgetLoan", back_populates="gadget", cascade="all, delete-orphan")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)  # e.g. MAIN, NORD, SUD
    is_active = Column(Boolean, default=True, nullable=False)

    stocks = relationship("GadgetVariantStock", back_populates="warehouse", cascade="all, delete-orphan")


class GadgetVariantStock(Base):
    __tablename__ = "gadget_variant_stocks"

    id = Column(Integer, primary_key=True)
    gadget_id = Column(Integer, ForeignKey("gadgets.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)

    gadget = relationship("Gadget", back_populates="stocks")
    warehouse = relationship("Warehouse", back_populates="stocks")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    gadget_id = Column(Integer, ForeignKey("gadgets.id"), nullable=False)
    
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)  # Null if RESTOCK
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)    # Null if DELIVERY

    quantity = Column(Integer, nullable=False)
    movement_type = Column(String, nullable=False)  # RESTOCK, TRANSFER, DELIVERY, LOAN, LOAN_RETURN
    
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User ID of Secretary/Admin
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(String, nullable=True)

    gadget = relationship("Gadget", back_populates="movements")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    performer = relationship("User", foreign_keys=[performed_by])


class GadgetLock(Base):
    __tablename__ = "gadget_locks"

    gadget_id = Column(Integer, ForeignKey("gadgets.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    locked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    gadget = relationship("Gadget")
    user = relationship("User")


class GadgetLoan(Base):
    __tablename__ = "gadget_loans"

    id = Column(Integer, primary_key=True)
    gadget_id = Column(Integer, ForeignKey("gadgets.id"), nullable=False)
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    returned_quantity = Column(Integer, default=0, nullable=False)
    distributed_quantity = Column(Integer, default=0, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)  # ACTIVE, PARTIAL, RETURNED
    loan_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_return_date = Column(DateTime, nullable=True)
    returned_date = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    gadget = relationship("Gadget", back_populates="loans")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to_user_id])
    performer = relationship("User", foreign_keys=[performed_by])

