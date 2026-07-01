from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import time
import logging

#-----Logging Steup------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

#-----CONSTANTS-------
PRICE_SELECTORS = [
    "div.v1zwn21l.v1zwn20._1psv1zeb9._1psv1ze0",  # confirmed working (Day 1)
    "div._30jeq3",                                   # older template fallback
    "div.Nx9bqj",                                    # another known variant
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

#---------VALIDATION-----------
#URL Validation -> Reject URLs that aren't valid Flipkart product links early

def is_valid_flipkart_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https") and
            "flipkart.com" in parsed.netloc
        )
    except Exception:
        return False
    
#-----------FETCHING--------------

def get_rendered_html(url: str, retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching URL (attempt {attempt}): {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, timeout=20000, wait_until="networkidle")
                html = page.content()
                browser.close()
            return html
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(2)
            else:
                logger.error(f"All {retries} attempts failed for URL: {url}")
                raise
    
#----------Parsing helpers--------------
            
def extract_price(soup) -> str | None:
    for selector in PRICE_SELECTORS:
        tag = soup.select_one(selector)
        if tag:
            logger.info(f"Price found using selector: {selector}")
            return tag.get_text(strip=True)
    logger.warning("No price found with any known selector")
    return None
            
            
def check_availability(soup) -> str:
    out_of_stock_phrases = [
        "sold out",
        "out of stock",
        "currently unavailable",
        "notify me",
    ]
    page_text = soup.get_text(separator=" ").lower()
    for phrase in out_of_stock_phrases:
        if phrase in page_text:
            logger.info("Product is out of stock")
            return "out_of_stock"
    return "in_stock"


def clean_title(raw_title: str) -> str | None:
    if not raw_title:
        return None
    for separator in [" - Buy", " | "]:
        if separator in raw_title:
            return raw_title.split(separator)[0].strip()
    return raw_title.strip()


def clean_price(price_raw: str) -> float | None:
    if not price_raw:
        return None
    digits = re.sub(r"[^\d]", "", price_raw)
    return float(digits) if digits else None


#---------Main Public Function-------------------
def scrape_flipkart_product(url: str) -> dict:
    if not is_valid_flipkart_url(url):
        logger.error(f"Invalid Flipkart URL: {url}")
        return {"url": url, "error": "invalid_url"}

    try:
        html = get_rendered_html(url)
    except Exception as e:
        return {"url": url, "error": f"fetch_failed: {str(e)}"}

    soup = BeautifulSoup(html, "lxml")

    raw_title = soup.title.get_text(strip=True) if soup.title else None
    price_raw = extract_price(soup)
    availability = check_availability(soup)

    title = clean_title(raw_title)
    price = clean_price(price_raw)
    
    result = {
        "url": url,
        "title": title,
        "price": price,
        "price_raw": price_raw,
        "availability": availability,
    }

    logger.info(f"Scraped: {title} | {price_raw} | {availability}")
    return result

#-------Test run---------------

if __name__ == "__main__":
    test_urls = [
        "https://www.flipkart.com/vebnor-solid-men-polo-neck-light-green-t-shirt/p/itm83671e2bbcec7",
        "https://www.flipkart.com/layasa-men-slippers/p/itm1a826eecef1ad",
        "https://www.invalidurl.com/product",   # should return invalid_url error
    ]

    for url in test_urls:
        result = scrape_flipkart_product(url)
        print(result)
        print("-" * 60)