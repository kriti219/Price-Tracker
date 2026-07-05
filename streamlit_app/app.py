import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent.parent / ".env")

from api_client import (
    add_product,
    get_all_products,
    get_price_history,
    deactivate_product,
    update_target_price,
    check_api_health,
)
from charts import build_price_history_chart, build_price_stats

import logging
logger = logging.getLogger(__name__)

# ── Supabase client ───────────────────────────────────────────────────────────

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY"),
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Flipkart Price Tracker",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header { font-size:2.2rem; font-weight:700; color:#2874f0; margin-bottom:0; }
    .sub-header  { font-size:1rem; color:#888; margin-top:0; margin-bottom:2rem; }
    .auth-title  { font-size:1.8rem; font-weight:700; color:#2874f0; text-align:center; }
    .auth-sub    { color:#888; font-size:0.95rem; text-align:center; margin-bottom:1.5rem; }
    .badge-instock    { background:#d4edda; color:#155724; padding:3px 10px;
                        border-radius:12px; font-size:0.8rem; font-weight:600; }
    .badge-outofstock { background:#f8d7da; color:#721c24; padding:3px 10px;
                        border-radius:12px; font-size:0.8rem; font-weight:600; }
    .badge-unknown    { background:#e2e3e5; color:#383d41; padding:3px 10px;
                        border-radius:12px; font-size:0.8rem; font-weight:600; }
    .price-drop  { color:#28a745; font-weight:700; }
    .price-above { color:#dc3545; font-weight:700; }
    div[data-testid="metric-container"] {
        background:#f8f9fa; border:1px solid #e0e0e0;
        border-radius:8px; padding:16px;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# ── API health check ──────────────────────────────────────────────────────────

if not check_api_health():
    st.error(
        "Cannot connect to the FastAPI backend. "
        "Run: `uvicorn main:app --reload`",
        icon="🔴",
    )
    st.stop()


# ── Auth screen ───────────────────────────────────────────────────────────────

def show_auth_screen():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(
            '<p class="auth-title">🏷️ Flipkart Price Tracker</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="auth-sub">Track prices. Get alerted when they drop.</p>',
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

        # ── Sign In ───────────────────────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="••••••••",
                )
                login_btn = st.form_submit_button(
                    "Sign In",
                    use_container_width=True,
                    type="primary",
                )

            if login_btn:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    with st.spinner("Signing in..."):
                        try:
                            response = supabase.auth.sign_in_with_password({
                                "email": email.strip(),
                                "password": password,
                            })
                            st.session_state.access_token = (
                                response.session.access_token
                            )
                            st.session_state.user_email = response.user.email
                            st.success("Signed in successfully!")
                            st.rerun()
                        except Exception as e:
                            error_msg = str(e)
                            if "Invalid login credentials" in error_msg:
                                st.error("Incorrect email or password.")
                            elif "Email not confirmed" in error_msg:
                                st.error(
                                    "Please verify your email "
                                    "before signing in."
                                )
                            else:
                                st.error(f"Sign in failed: {error_msg}")

        # ── Sign Up ───────────────────────────────────────────────────────────
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                )
                new_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Minimum 8 characters",
                )
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-enter password",
                )
                signup_btn = st.form_submit_button(
                    "Create Account",
                    use_container_width=True,
                    type="primary",
                )

            if signup_btn:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif "@" not in new_email:
                    st.error("Please enter a valid email address")
                elif len(new_password) < 8:
                    st.error("Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    with st.spinner("Creating your account..."):
                        try:
                            response = supabase.auth.sign_up({
                                "email": new_email.strip(),
                                "password": new_password,
                            })
                            if response.user:
                                if response.session:
                                    st.session_state.access_token = (
                                        response.session.access_token
                                    )
                                    st.session_state.user_email = (
                                        response.user.email
                                    )
                                    st.success("Account created! Welcome.")
                                    st.rerun()
                                else:
                                    st.success(
                                        "Account created! Check your email "
                                        "to confirm, then sign in."
                                    )
                        except Exception as e:
                            error_msg = str(e)
                            if "already registered" in error_msg.lower():
                                st.error(
                                    "An account with this email already "
                                    "exists. Please sign in."
                                )
                            else:
                                st.error(f"Sign up failed: {error_msg}")


# ── Dashboard ─────────────────────────────────────────────────────────────────

def show_dashboard():
    token = st.session_state.access_token
    user_email = st.session_state.user_email

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"**Signed in as:**")
        st.markdown(f"`{user_email}`")

        if st.button("Sign Out", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            st.session_state.access_token = None
            st.session_state.user_email = None
            st.rerun()

        st.divider()
        st.markdown("**➕ Track a New Product**")

        with st.form("add_product_form", clear_on_submit=True):
            product_url = st.text_input(
                "Flipkart Product URL",
                placeholder="https://www.flipkart.com/product/p/...",
            )
            target_price = st.number_input(
                "Target Price (₹)",
                min_value=1.0,
                max_value=1000000.0,
                value=500.0,
                step=50.0,
                help="Alert me when price drops to or below this",
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
            else:
                with st.sidebar:
                    with st.spinner(
                        "Scraping product, please wait 15-20 seconds..."
                    ):
                        result = add_product(
                            url=product_url.strip(),
                            target_price=target_price,
                            token=token,
                        )

                if result["status_code"] == 201:
                    st.sidebar.success(
                        f"Now tracking: "
                        f"**{result['data'].get('title', 'Product')}**"
                    )
                    st.rerun()
                elif result["status_code"] == 409:
                    st.sidebar.warning(
                        "You are already tracking this product."
                    )
                elif result["status_code"] == 401:
                    st.sidebar.error("Session expired. Please sign in again.")
                    st.session_state.access_token = None
                    st.rerun()
                else:
                    st.sidebar.error(
                        f"Failed: "
                        f"{result['data'].get('detail', 'Unknown error')}"
                    )

        st.sidebar.divider()
        st.sidebar.caption(
            "Prices auto-update every 6 hours via GitHub Actions."
        )

    # ── Header ────────────────────────────────────────────────────────────────

    st.markdown(
        '<p class="main-header">🏷️ Flipkart Price Tracker</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">'
        'Track product prices and get alerted when they drop'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── Load products ─────────────────────────────────────────────────────────

    products = get_all_products(token=token)
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

    # ── Metrics ───────────────────────────────────────────────────────────────

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tracked", len(active_products))
    with col2:
        st.metric("Below Target 🎉", len(below_target))
    with col3:
        st.metric("Out of Stock", len(unavailable))
    with col4:
        st.metric("Last Refreshed", datetime.now().strftime("%H:%M"))

    st.divider()

    # ── Product table ─────────────────────────────────────────────────────────

    def render_product_table(product_list: list, key_prefix: str = ""):
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
                    availability = product.get(
                        "latest_availability", "unknown"
                    )

                    price_col, target_col, status_col = st.columns(3)

                    with price_col:
                        if latest_price is not None:
                            is_below = latest_price <= target_price
                            css = "price-drop" if is_below else "price-above"
                            st.markdown(
                                f'<span class="{css}">'
                                f'₹{latest_price:,.0f}</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown("—")
                        st.caption("Current Price")

                    with target_col:
                        st.markdown(f"**₹{target_price:,.0f}**")
                        st.caption("Target Price")

                    with status_col:
                        if availability == "in_stock":
                            badge = (
                                '<span class="badge-instock">In Stock</span>'
                            )
                        elif availability == "out_of_stock":
                            badge = (
                                '<span class="badge-outofstock">'
                                'Out of Stock</span>'
                            )
                        else:
                            badge = (
                                '<span class="badge-unknown">Unknown</span>'
                            )
                        st.markdown(badge, unsafe_allow_html=True)
                        st.caption("Availability")

                with action_col:
                    if product.get("is_active"):
                        with st.expander("✏️ Edit"):
                            new_price = st.number_input(
                                "New target (₹)",
                                min_value=1.0,
                                max_value=1000000.0,
                                value=float(
                                    product.get("target_price", 500)
                                ),
                                step=50.0,
                                key=f"{key_prefix}price_input_"
                                    f"{product['id']}",
                            )
                            if st.button(
                                "Update",
                                key=f"{key_prefix}update_{product['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                result = update_target_price(
                                    product_id=product["id"],
                                    new_target_price=new_price,
                                    token=token,
                                )
                                if result["status_code"] == 200:
                                    st.success("Updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed.")

                        if st.button(
                            "Stop",
                            key=f"{key_prefix}deactivate_{product['id']}",
                            help="Stop tracking this product",
                            type="secondary",
                            use_container_width=True,
                        ):
                            result = deactivate_product(
                                product["id"], token=token
                            )
                            if result["status_code"] == 200:
                                st.success("Stopped tracking.")
                                st.rerun()
                            else:
                                st.error("Failed to deactivate.")
                    else:
                        st.markdown("*Inactive*")

                # ── Price history chart ───────────────────────────────────────
                with st.expander("📈 View price history", expanded=False):
                    history = get_price_history(
                        product_id=product["id"],
                        token=token,
                        limit=100,
                    )

                    if not history:
                        st.info(
                            "No price history yet. "
                            "Data will appear after the next scrape run."
                        )
                    else:
                        stats = build_price_stats(
                            history,
                            product.get("target_price", 0),
                        )

                        if stats:
                            s1, s2, s3, s4 = st.columns(4)
                            with s1:
                                st.metric(
                                    "Lowest",
                                    f"₹{stats['lowest']:,.0f}",
                                )
                            with s2:
                                st.metric(
                                    "Highest",
                                    f"₹{stats['highest']:,.0f}",
                                )
                            with s3:
                                st.metric(
                                    "Average",
                                    f"₹{stats['average']:,.0f}",
                                )
                            with s4:
                                st.metric(
                                    "Below Target",
                                    f"{stats['times_below_target']}/"
                                    f"{stats['in_stock_records']} checks",
                                )

                        fig = build_price_history_chart(
                            history=history,
                            target_price=product.get("target_price", 0),
                            product_title=product.get("title") or "Product",
                        )

                        if fig:
                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                                key=f"{key_prefix}chart_{product['id']}",
                                config={
                                    "displayModeBar": True,
                                    "modeBarButtonsToRemove": [
                                        "lasso2d", "select2d"
                                    ],
                                    "displaylogo": False,
                                },
                            )
                        else:
                            st.info(
                                "Not enough data to render chart yet."
                            )

                        if st.checkbox(
                            "Show raw data",
                            key=f"{key_prefix}raw_{product['id']}",
                        ):
                            import pandas as pd
                            df = pd.DataFrame(history)
                            df["scraped_at"] = pd.to_datetime(
                                df["scraped_at"]
                            ).dt.strftime("%d %b %Y %H:%M")
                            df = df.rename(columns={
                                "scraped_at": "Scraped At",
                                "price": "Price (₹)",
                                "price_raw": "Raw Price",
                                "availability": "Availability",
                            })
                            st.dataframe(
                                df[[
                                    "Scraped At", "Price (₹)",
                                    "Raw Price", "Availability"
                                ]],
                                use_container_width=True,
                                hide_index=True,
                            )

                st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────

    if not products:
        st.info(
            "You are not tracking any products yet. "
            "Use the sidebar to add your first product.",
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

    # ── Refresh button ────────────────────────────────────────────────────────

    col_left, col_right = st.columns([5, 1])
    with col_right:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────

if st.session_state.access_token is None:
    show_auth_screen()
else:
    show_dashboard()