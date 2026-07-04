import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime
from api_client import (
    add_product,
    get_all_products,
    deactivate_product,
    check_api_health,
)

# ── Page configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Flipkart Price Tracker",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #2874f0;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #888888;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    .badge-instock {
        background-color: #d4edda;
        color: #155724;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-outofstock {
        background-color: #f8d7da;
        color: #721c24;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-unknown {
        background-color: #e2e3e5;
        color: #383d41;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .price-drop {
        color: #28a745;
        font-weight: 700;
    }
    .price-above {
        color: #dc3545;
        font-weight: 700;
    }
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
    }
    .sidebar-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #2874f0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── API health check ──────────────────────────────────────────────────────────

if not check_api_health():
    st.error(
        "Cannot connect to the FastAPI backend. "
        "Make sure it is running with: `uvicorn main:app --reload`",
        icon="🔴",
    )
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<p class="main-header">🛒 Flipkart Price Tracker</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Track product prices and get alerted when they drop</p>',
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="sidebar-title">➕ Track a New Product</p>', unsafe_allow_html=True)
    st.markdown("Paste a Flipkart product URL below to start tracking its price.")

    with st.form("add_product_form", clear_on_submit=True):
        product_url = st.text_input(
            "Flipkart Product URL",
            placeholder="https://www.flipkart.com/product/p/...",
            help="Copy the URL from any Flipkart product page",
        )
        user_email = st.text_input(
            "Your Email",
            placeholder="you@example.com",
            help="We will email you when the price drops",
        )
        target_price = st.number_input(
            "Target Price (₹)",
            min_value=1.0,
            max_value=1000000.0,
            value=500.0,
            step=50.0,
            help="Get alerted when price drops to or below this amount",
        )
        submitted = st.form_submit_button(
            "Start Tracking",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not product_url.strip():
            st.sidebar.error("Please enter a product URL")
        elif "flipkart.com" not in product_url:
            st.sidebar.error("Only Flipkart URLs are supported")
        elif not user_email.strip() or "@" not in user_email:
            st.sidebar.error("Please enter a valid email address")
        else:
            with st.sidebar:
                with st.spinner("Scraping product page, this may take 15-20 seconds..."):
                    result = add_product(
                        url=product_url.strip(),
                        user_email=user_email.strip(),
                        target_price=target_price,
                    )

            if result["status_code"] == 201:
                product_data = result["data"]
                st.sidebar.success(
                    f"Now tracking: **{product_data.get('title', 'Product')}**"
                )
                st.rerun()
            elif result["status_code"] == 409:
                st.sidebar.warning("This URL is already being tracked.")
            else:
                detail = result["data"].get("detail", "Unknown error")
                st.sidebar.error(f"Failed to add product: {detail}")

    st.sidebar.divider()
    st.sidebar.caption(
        "Prices are checked automatically every 6 hours via GitHub Actions."
    )

# ── Load products ─────────────────────────────────────────────────────────────

products = get_all_products()

# ── Summary metrics ───────────────────────────────────────────────────────────

active_products = [p for p in products if p.get("is_active")]
below_target = [
    p for p in active_products
    if p.get("latest_price") is not None
    and p.get("latest_price") <= p.get("target_price", float("inf"))
]
unavailable = [
    p for p in active_products
    if p.get("latest_availability") == "out_of_stock"
]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Tracked", len(active_products))
with col2:
    st.metric("Below Target 🎉", len(below_target))
with col3:
    st.metric("Out of Stock", len(unavailable))
with col4:
    st.metric(
        "Last Refreshed",
        datetime.now().strftime("%H:%M"),
        help="Prices update every 6 hours via GitHub Actions.",
    )

st.divider()

# ── Product table ─────────────────────────────────────────────────────────────

def render_product_table(product_list: list, key_prefix: str = ""):
    """Render a list of products with action buttons."""

    if not product_list:
        st.info("No products in this view.")
        return

    for product in product_list:
        with st.container():
            info_col, action_col = st.columns([5, 1])

            with info_col:
                title = product.get("title") or "Untitled Product"
                url = product.get("url", "")
                st.markdown(f"**[{title}]({url})**")

                latest_price = product.get("latest_price")
                target_price = product.get("target_price")
                availability = product.get("latest_availability", "unknown")

                price_col, target_col, status_col, email_col = st.columns(4)

                with price_col:
                    if latest_price is not None:
                        is_below = latest_price <= target_price
                        price_class = "price-drop" if is_below else "price-above"
                        st.markdown(
                            f'<span class="{price_class}">₹{latest_price:,.0f}</span>',
                            unsafe_allow_html=True,
                        )
                        st.caption("Current Price")
                    else:
                        st.markdown("—")
                        st.caption("Current Price")

                with target_col:
                    st.markdown(f"**₹{target_price:,.0f}**")
                    st.caption("Target Price")

                with status_col:
                    if availability == "in_stock":
                        badge = '<span class="badge-instock">In Stock</span>'
                    elif availability == "out_of_stock":
                        badge = '<span class="badge-outofstock">Out of Stock</span>'
                    else:
                        badge = '<span class="badge-unknown">Unknown</span>'
                    st.markdown(badge, unsafe_allow_html=True)
                    st.caption("Availability")

                with email_col:
                    st.markdown(product.get("user_email", "—"))
                    st.caption("Alert Email")

            with action_col:
                if product.get("is_active"):
                    # key_prefix ensures unique keys across tabs
                    if st.button(
                        "Stop",
                        key=f"{key_prefix}deactivate_{product['id']}",
                        help="Stop tracking this product",
                        type="secondary",
                    ):
                        result = deactivate_product(product["id"])
                        if result["status_code"] == 200:
                            st.success("Stopped tracking.")
                            st.rerun()
                        else:
                            st.error("Failed to deactivate.")
                else:
                    st.markdown("*Inactive*")

            st.divider()


# ── Tabs ──────────────────────────────────────────────────────────────────────

if not products:
    st.info(
        "No products being tracked yet. "
        "Add your first product using the sidebar form.",
        icon="👈",
    )
else:
    tab_active, tab_all = st.tabs([
        f"Active ({len(active_products)})",
        f"All Products ({len(products)})",
    ])

    with tab_active:
        render_product_table(active_products, key_prefix="active_")

    with tab_all:
        render_product_table(products, key_prefix="all_")

# ── Refresh button ────────────────────────────────────────────────────────────

col_left, col_right = st.columns([5, 1])
with col_right:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()