import os
import requests
import logging

logger = logging.getLogger(__name__)

TIMEOUT = 60


def get_api_base_url() -> str:
    """
    Read API_BASE_URL at call time, not import time.
    Tries st.secrets first, falls back to environment variable,
    then falls back to localhost for local development.
    """
    try:
        import streamlit as st
        return st.secrets.get("API_BASE_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    except Exception:
        return os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def check_api_health() -> bool:
    """
    Returns True if FastAPI is reachable.
    Uses a longer timeout and retries once to handle
    Render free tier cold starts (30-60 seconds).
    """
    api_url = get_api_base_url()
    for attempt in range(2):  # try twice
        try:
            response = requests.get(
                f"{api_url}/",
                timeout=30,  # increased from 5 to 30
            )
            if response.status_code == 200:
                return True
        except Exception:
            if attempt == 0:
                import time
                time.sleep(5)  # wait 5 seconds before retry
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