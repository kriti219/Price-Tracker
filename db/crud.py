import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.models import Product, PriceHistory

logger = logging.getLogger(__name__)


# ── Product operations ────────────────────────────────────────────────────────

def create_product(
    db: Session,
    url: str,
    user_email: str,
    target_price: float,
    title: Optional[str] = None,
) -> Product:
    """
    Add a new product to track.
    Raises ValueError if the URL is already being tracked.
    """
    existing = get_product_by_url(db, url)
    if existing:
        raise ValueError(f"URL is already being tracked (product id={existing.id})")

    product = Product(
        url=url,
        title=title,
        user_email=user_email,
        target_price=target_price,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    logger.info(f"Created product id={product.id}: {url}")
    return product


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """
    Fetch a single product by its primary key.
    Returns None if not found.
    """
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_url(db: Session, url: str) -> Optional[Product]:
    """
    Check if a URL is already being tracked.
    Returns the Product if found, None otherwise.
    """
    return db.query(Product).filter(Product.url == url).first()


def get_all_products(db: Session) -> list[Product]:
    """
    Return all products (active and inactive),
    newest first. Used by the dashboard.
    """
    return (
        db.query(Product)
        .order_by(desc(Product.created_at))
        .all()
    )


def get_active_products(db: Session) -> list[Product]:
    """
    Return only products that are still being tracked.
    Used by the scraper to know what to check.
    """
    return (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(desc(Product.created_at))
        .all()
    )


def deactivate_product(db: Session, product_id: int) -> Optional[Product]:
    """
    Stop tracking a product (soft delete).
    Sets is_active=False instead of deleting the row,
    so price history is preserved.
    """
    product = get_product_by_id(db, product_id)
    if not product:
        logger.warning(f"Tried to deactivate non-existent product id={product_id}")
        return None
    product.is_active = False
    db.commit()
    db.refresh(product)
    logger.info(f"Deactivated product id={product_id}")
    return product


def update_product_title(db: Session, product_id: int, title: str) -> Optional[Product]:
    """
    Update a product's title after first successful scrape.
    Title isn't known at submission time, only after scraping.
    """
    product = get_product_by_id(db, product_id)
    if not product:
        return None
    product.title = title
    db.commit()
    db.refresh(product)
    return product


# ── Price history operations ──────────────────────────────────────────────────

def add_price_history(
    db: Session,
    product_id: int,
    price: Optional[float],
    price_raw: Optional[str],
    availability: str = "unknown",
) -> PriceHistory:
    """
    Insert a new price record after every scrape run.
    Called once per product per scrape cycle.
    """
    record = PriceHistory(
        product_id=product_id,
        price=price,
        price_raw=price_raw,
        availability=availability,
        scraped_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(
        f"Added price history for product id={product_id}: "
        f"{price_raw} ({availability})"
    )
    return record


def get_price_history(
    db: Session,
    product_id: int,
    limit: int = 100,
) -> list[PriceHistory]:
    """
    Return all price history rows for a product, newest first.
    Limit controls how many data points the chart loads.
    """
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(desc(PriceHistory.scraped_at))
        .limit(limit)
        .all()
    )


def get_latest_price(db: Session, product_id: int) -> Optional[PriceHistory]:
    """
    Return just the most recent price record for a product.
    Used by the alert checker to compare against target_price.
    """
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(desc(PriceHistory.scraped_at))
        .first()
    )


# ── Alert logic ───────────────────────────────────────────────────────────────

def check_price_alert(db: Session, product_id: int) -> dict:
    """
    Check if the latest scraped price is at or below
    the user's target price threshold.

    Returns a dict with:
    - should_alert (bool): True if alert email should be sent
    - current_price (float): latest scraped price
    - target_price (float): user's threshold
    - product: the Product object (for email content)
    """
    product = get_product_by_id(db, product_id)
    if not product:
        return {"should_alert": False, "reason": "product_not_found"}

    latest = get_latest_price(db, product_id)
    if not latest or latest.price is None:
        return {"should_alert": False, "reason": "no_price_data"}

    if latest.availability == "out_of_stock":
        return {"should_alert": False, "reason": "out_of_stock"}

    should_alert = latest.price <= product.target_price

    return {
        "should_alert": should_alert,
        "current_price": latest.price,
        "target_price": product.target_price,
        "product": product,
        "reason": "price_dropped" if should_alert else "price_above_target",
    }