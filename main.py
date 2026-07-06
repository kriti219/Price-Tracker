import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from db.connection import engine, Base, get_db
from db import crud
from schemas import (
    ProductCreate,
    ProductResponse,
    ProductDetailResponse,
    PriceHistoryResponse,
    MessageResponse,
    TargetPriceUpdate,
)
from scraper import scrape_flipkart_product
from auth.supabase_auth import get_user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

security = HTTPBearer()


# ── JWT dependency ────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Verify the Supabase JWT from the Authorization header.
    Raises 401 if token is missing, invalid, or expired.
    """
    token = credentials.credentials
    user = get_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
        )
    return user


# ── App startup ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: ensuring tables exist")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Flipkart Price Tracker API",
    description="Track product prices and get alerted when they drop",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_model=MessageResponse)
def root():
    return {"message": "Flipkart Price Tracker API is running"}


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_product(
    payload: ProductCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new product to track. Requires authentication."""
    existing = crud.get_product_by_url(db, payload.url, user_id=str(current_user.id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You are already tracking this URL (product id={existing.id})",
        )

    logger.info(f"Scraping on submission for user {current_user.id}: {payload.url}")
    scraped = scrape_flipkart_product(payload.url)

    if "error" in scraped:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not scrape product: {scraped['error']}",
        )

    product = crud.create_product(
        db=db,
        url=payload.url,
        user_email=current_user.email,
        target_price=payload.target_price,
        user_id=str(current_user.id),
        title=scraped.get("title"),
    )

    crud.add_price_history(
        db=db,
        product_id=product.id,
        price=scraped.get("price"),
        price_raw=scraped.get("price_raw"),
        availability=scraped.get("availability", "unknown"),
    )
    
    logger.info(
        f"Product added: id={product.id}, title={product.title}"
    )

    return product


@app.get("/products", response_model=list[ProductDetailResponse])
def list_products(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all products for the authenticated user only."""
    products = crud.get_products_by_user_id(db, str(current_user.id))
    result = []
    for product in products:
        latest = crud.get_latest_price(db, product.id)
        result.append(
            ProductDetailResponse(
                id=product.id,
                url=product.url,
                title=product.title,
                user_email=product.user_email,
                target_price=product.target_price,
                is_active=product.is_active,
                created_at=product.created_at,
                latest_price=latest.price if latest else None,
                latest_availability=latest.availability if latest else None,
            )
        )
    return result


@app.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single product. Only accessible by its owner."""
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if str(product.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your product")

    latest = crud.get_latest_price(db, product_id)
    return ProductDetailResponse(
        id=product.id,
        url=product.url,
        title=product.title,
        user_email=product.user_email,
        target_price=product.target_price,
        is_active=product.is_active,
        created_at=product.created_at,
        latest_price=latest.price if latest else None,
        latest_availability=latest.availability if latest else None,
    )


@app.get(
    "/products/{product_id}/history",
    response_model=list[PriceHistoryResponse],
)
def get_price_history(
    product_id: int,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get price history for a product. Only accessible by its owner."""
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if str(product.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your product")

    return crud.get_price_history(db, product_id, limit=limit)


@app.delete("/products/{product_id}", response_model=MessageResponse)
def deactivate_product(
    product_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stop tracking a product. Only the owner can deactivate."""
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if str(product.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your product")

    crud.deactivate_product(db, product_id)
    return {"message": f"Product id={product_id} deactivated"}


@app.patch("/products/{product_id}/target", response_model=ProductResponse)
def update_target_price(
    product_id: int,
    payload: TargetPriceUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update target price for a product. Only the owner can update."""
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if str(product.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your product")

    updated = crud.update_target_price(db, product_id, payload.target_price)
    return updated