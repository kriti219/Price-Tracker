from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String,
    Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from db.connection import Base


class Product(Base):
    __tablename__ = "products"

    id            = Column(Integer, primary_key=True, index=True)
    url           = Column(Text, unique=True, nullable=False)
    title         = Column(String(500), nullable=True)
    user_email    = Column(String(255), nullable=False)
    target_price  = Column(Float, nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    price_history = relationship(
        "PriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Product id={self.id} title={self.title!r}>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id           = Column(Integer, primary_key=True, index=True)
    product_id   = Column(Integer, ForeignKey("products.id"), nullable=False)
    price        = Column(Float, nullable=True)
    price_raw    = Column(String(50), nullable=True)
    availability = Column(String(50), default="unknown")
    scraped_at   = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory product_id={self.product_id} price={self.price}>"