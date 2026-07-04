import logging
import sys
from datetime import datetime

from db.connection import SessionLocal
from db import crud
from scraper import scrape_flipkart_product
from email_alert import send_price_alert

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Alert stub (will be replaced on Day 8) ───────────────────────────────────

from email_alert import send_price_alert

def send_alert_email(product, current_price: float):
    """
    Send a real price drop alert email via Resend.
    """
    logger.info(
        f"Price drop detected for '{product.title}': "
        f"₹{current_price} ≤ target ₹{product.target_price} "
        f"→ sending alert to {product.user_email}"
    )
    success = send_price_alert(
        product_title=product.title or product.url,
        current_price=current_price,
        target_price=product.target_price,
        product_url=product.url,
        recipient_email=product.user_email,
    )
    if not success:
        logger.warning(
            f"Alert email failed for product id={product.id}. "
            f"Check RESEND_API_KEY and ALERT_TO_EMAIL in your .env"
        )


# ── Core job logic ────────────────────────────────────────────────────────────

def run_scrape_job():
    logger.info("=" * 60)
    logger.info(f"Scrape job started at {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # Step 1: Get all active products
        products = crud.get_active_products(db)

        if not products:
            logger.info("No active products to scrape. Exiting.")
            return

        logger.info(f"Found {len(products)} active product(s) to scrape")

        # Counters for summary log at the end
        success_count = 0
        fail_count = 0
        alert_count = 0

        # Step 2: Loop through each product
        for product in products:
            logger.info("-" * 40)
            logger.info(f"Scraping product id={product.id}: {product.title or product.url}")

            # Step 3: Scrape current price
            result = scrape_flipkart_product(product.url)

            # Step 4: Handle scrape failure
            if "error" in result:
                logger.warning(
                    f"Scrape failed for product id={product.id}: {result['error']}"
                )
                # Still store a record so we have a paper trail of failures
                crud.add_price_history(
                    db=db,
                    product_id=product.id,
                    price=None,
                    price_raw=None,
                    availability="scrape_failed",
                )
                fail_count += 1
                continue

            # Step 5: Store the new price history row
            price = result.get("price")
            price_raw = result.get("price_raw")
            availability = result.get("availability", "unknown")

            crud.add_price_history(
                db=db,
                product_id=product.id,
                price=price,
                price_raw=price_raw,
                availability=availability,
            )

            logger.info(
                f"Stored price for product id={product.id}: "
                f"{price_raw} | {availability}"
            )

            # Step 6: Update title if it was missing or changed
            scraped_title = result.get("title")
            if scraped_title and scraped_title != product.title:
                crud.update_product_title(db, product.id, scraped_title)
                logger.info(
                    f"Updated title for product id={product.id}: {scraped_title}"
                )

            # Step 7: Check if alert should fire
            alert_check = crud.check_price_alert(db, product.id)

            if alert_check.get("should_alert"):
                send_alert_email(product, alert_check["current_price"])
                alert_count += 1

            success_count += 1

        # Step 8: Print summary
        logger.info("=" * 60)
        logger.info(
            f"Scrape job finished | "
            f"Success: {success_count} | "
            f"Failed: {fail_count} | "
            f"Alerts fired: {alert_count}"
        )
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Unexpected error in scrape job: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_scrape_job()