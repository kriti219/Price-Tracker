import os
import requests
import logging

logger = logging.getLogger(__name__)

TIMEOUT = 60


def get_api_base_url() -> str:
    """
    Read API_BASE_URL with multiple fallbacks.
    Priority: st.secrets → environment variable → localhost
    """
    # Try Streamlit secrets first (deployed environment)
    try:
        import streamlit as st
        if "API_BASE_URL" in st.secrets:
            return st.secrets["API_BASE_URL"]
    except Exception:
        pass

    # Try environment variable (local development)
    env_url = os.getenv("API_BASE_URL")
    if env_url:
        return env_url

    # Final fallback
    return "http://127.0.0.1:8000"


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def check_api_health() -> bool:
    api_url = get_api_base_url()
    logger.info(f"Health check URL: {api_url}")  # add this
    for attempt in range(2):
        try:
            response = requests.get(
                f"{api_url}/",
                timeout=30,
            )
            if response.status_code == 200:
                return True
        except Exception as e:
            logger.error(f"Health check attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                import time
                time.sleep(5)
    return False


def add_product(url: str, target_price: float, token: str) -> dict:
    api_url = get_api_base_url()
    try:
        response = requests.post(
            f"{api_url}/products",
            json={"url": url, "target_price": target_price},
            headers=_auth_headers(token),
            timeout=TIMEOUT,
        )
        return {"status_code": response.status_code, "data": response.json()}
    except requests.exceptions.ConnectionError:
        return {"status_code": 503, "data": {"detail": "Cannot connect to API."}}
    except Exception as e:
        return {"status_code": 500, "data": {"detail": str(e)}}


def get_all_products(token: str) -> list:
    api_url = get_api_base_url()
    try:
        response = requests.get(
            f"{api_url}/products",
            headers=_auth_headers(token),
            timeout=TIMEOUT,
        )
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []


def get_price_history(product_id: int, token: str, limit: int = 50) -> list:
    api_url = get_api_base_url()
    try:
        response = requests.get(
            f"{api_url}/products/{product_id}/history",
            headers=_auth_headers(token),
            params={"limit": limit},
            timeout=TIMEOUT,
        )
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []


def deactivate_product(product_id: int, token: str) -> dict:
    api_url = get_api_base_url()
    try:
        response = requests.delete(
            f"{api_url}/products/{product_id}",
            headers=_auth_headers(token),
            timeout=TIMEOUT,
        )
        return {"status_code": response.status_code, "data": response.json()}
    except requests.exceptions.ConnectionError:
        return {"status_code": 503, "data": {"detail": "Cannot connect to API."}}
    except Exception as e:
        return {"status_code": 500, "data": {"detail": str(e)}}


def update_target_price(
    product_id: int,
    new_target_price: float,
    token: str,
) -> dict:
    api_url = get_api_base_url()
    try:
        response = requests.patch(
            f"{api_url}/products/{product_id}/target",
            json={"target_price": new_target_price},
            headers=_auth_headers(token),
            timeout=TIMEOUT,
        )
        return {"status_code": response.status_code, "data": response.json()}
    except requests.exceptions.ConnectionError:
        return {"status_code": 503, "data": {"detail": "Cannot connect to API."}}
    except Exception as e:
        return {"status_code": 500, "data": {"detail": str(e)}}