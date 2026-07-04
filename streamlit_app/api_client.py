import os
import requests
import logging

logger = logging.getLogger(__name__)

# When running locally FastAPI is on 8000
# On deployment this will be the Render URL (set via environment variable)
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

TIMEOUT = 60  # seconds, scraping takes time so keep this generous


def add_product(url: str, user_email: str, target_price: float) -> dict:
    """
    POST /products
    Add a new product to track.
    Returns the created product dict or an error dict.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/products",
            json={
                "url": url,
                "user_email": user_email,
                "target_price": target_price,
            },
            timeout=TIMEOUT,
        )
        return {"status_code": response.status_code, "data": response.json()}
    except requests.exceptions.ConnectionError:
        return {
            "status_code": 503,
            "data": {"detail": "Cannot connect to API. Make sure FastAPI is running."},
        }
    except Exception as e:
        return {"status_code": 500, "data": {"detail": str(e)}}


def get_all_products() -> list:
    """
    GET /products
    Returns list of all tracked products with latest price.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/products",
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.ConnectionError:
        return []
    except Exception:
        return []


def get_price_history(product_id: int, limit: int = 50) -> list:
    """
    GET /products/{id}/history
    Returns price history list for a product.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/products/{product_id}/history",
            params={"limit": limit},
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def deactivate_product(product_id: int) -> dict:
    """
    DELETE /products/{id}
    Stop tracking a product.
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/products/{product_id}",
            timeout=TIMEOUT,
        )
        return {"status_code": response.status_code, "data": response.json()}
    except requests.exceptions.ConnectionError:
        return {
            "status_code": 503,
            "data": {"detail": "Cannot connect to API."},
        }
    except Exception as e:
        return {"status_code": 500, "data": {"detail": str(e)}}


def check_api_health() -> bool:
    """
    GET /
    Returns True if FastAPI is reachable, False otherwise.
    Used to show a warning banner if backend is down.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False