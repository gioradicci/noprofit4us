from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
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

    variants = relationship("GadgetVariant", back_populates="gadget", cascade="all, delete-orphan")


class GadgetVariant(Base):
    __tablename__ = "gadget_variants"

    id = Column(Integer, primary_key=True)
    gadget_id = Column(Integer, ForeignKey("gadgets.id"), nullable=False)
    
    size = Column(String, nullable=True)          # e.g. S, M, L, XL
    color = Column(String, nullable=True)         # e.g. Blu, Nero, Rosso
    model = Column(String, nullable=True)         # e.g. Uomo, Donna, Unisex
    variant_type = Column(String, nullable=True)  # e.g. Metallic, Glow-in-the-dark
    
    sku = Column(String, unique=True, nullable=True)
    price_modifier = Column(Float, default=0.0)    # adjustment to min_donation
    stock_quantity = Column(Integer, default=0)    # Total aggregated stock
    image_path = Column(String, nullable=True)

    gadget = relationship("Gadget", back_populates="variants")
    stocks = relationship("GadgetVariantStock", back_populates="variant", cascade="all, delete-orphan")
    movements = relationship("StockMovement", back_populates="variant", cascade="all, delete-orphan")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)  # e.g. MAIN, NORD, SUD

    stocks = relationship("GadgetVariantStock", back_populates="warehouse", cascade="all, delete-orphan")


class GadgetVariantStock(Base):
    __tablename__ = "gadget_variant_stocks"

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey("gadget_variants.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)

    variant = relationship("GadgetVariant", back_populates="stocks")
    warehouse = relationship("Warehouse", back_populates="stocks")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey("gadget_variants.id"), nullable=False)
    
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)  # Null if RESTOCK
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)    # Null if DELIVERY

    quantity = Column(Integer, nullable=False)
    movement_type = Column(String, nullable=False)  # RESTOCK, TRANSFER, DELIVERY
    
    performed_by = Column(Integer, nullable=False)  # User ID of Secretary/Admin
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(String, nullable=True)

    variant = relationship("GadgetVariant", back_populates="movements")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
