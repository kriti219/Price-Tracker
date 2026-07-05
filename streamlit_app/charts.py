import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from typing import Optional


def build_price_history_chart(
    history: list,
    target_price: float,
    product_title: str,
) -> Optional[go.Figure]:
    """
    Build an interactive Plotly line chart for price history.

    Args:
        history: list of price history dicts from the API
        target_price: the user's alert threshold (shown as dashed line)
        product_title: used in chart title

    Returns:
        A Plotly Figure object, or None if there's not enough data
    """
    if not history:
        return None

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(history)
    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df = df.sort_values("scraped_at")  # oldest first for the chart

    # Separate in-stock and out-of-stock rows
    in_stock = df[
        (df["availability"] == "in_stock") &
        (df["price"].notna())
    ]
    out_of_stock = df[df["availability"] == "out_of_stock"]
    failed = df[df["availability"] == "scrape_failed"]

    if in_stock.empty:
        return None

    # Classify each in-stock point: below target (green) or above (red)
    below_target = in_stock[in_stock["price"] <= target_price]
    above_target = in_stock[in_stock["price"] > target_price]

    fig = go.Figure()

    # ── Main price line ───────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=in_stock["scraped_at"],
        y=in_stock["price"],
        mode="lines",
        name="Price",
        line=dict(color="#2874f0", width=2),
        hovertemplate=(
            "<b>%{y:,.0f}</b><br>"
            "%{x|%d %b %Y %H:%M}<br>"
            "<extra></extra>"
        ),
    ))

    # ── Points below target (green) ───────────────────────────────────────────
    if not below_target.empty:
        fig.add_trace(go.Scatter(
            x=below_target["scraped_at"],
            y=below_target["price"],
            mode="markers",
            name="At or below target",
            marker=dict(
                color="#28a745",
                size=10,
                symbol="circle",
                line=dict(color="white", width=1.5),
            ),
            hovertemplate=(
                "₹<b>%{y:,.0f}</b> ✅<br>"
                "%{x|%d %b %Y %H:%M}<br>"
                "<extra>Below target</extra>"
            ),
        ))

    # ── Points above target (red) ─────────────────────────────────────────────
    if not above_target.empty:
        fig.add_trace(go.Scatter(
            x=above_target["scraped_at"],
            y=above_target["price"],
            mode="markers",
            name="Above target",
            marker=dict(
                color="#dc3545",
                size=8,
                symbol="circle",
                line=dict(color="white", width=1.5),
            ),
            hovertemplate=(
                "₹<b>%{y:,.0f}</b><br>"
                "%{x|%d %b %Y %H:%M}<br>"
                "<extra>Above target</extra>"
            ),
        ))

    # ── Target price reference line ───────────────────────────────────────────
    fig.add_hline(
        y=target_price,
        line_dash="dash",
        line_color="#e74c3c",
        line_width=1.5,
        annotation_text=f"Target ₹{target_price:,.0f}",
        annotation_position="top right",
        annotation_font_color="#e74c3c",
    )

    # ── Out of stock markers ──────────────────────────────────────────────────
    if not out_of_stock.empty:
        # Show as vertical shaded regions or simple markers
        for _, row in out_of_stock.iterrows():
            fig.add_vline(
                x=row["scraped_at"].timestamp() * 1000,  # plotly needs ms
                line_dash="dot",
                line_color="#ffc107",
                line_width=1,
                opacity=0.5,
            )

        # Add a single legend entry for out of stock
        fig.add_trace(go.Scatter(
            x=out_of_stock["scraped_at"],
            y=[target_price] * len(out_of_stock),
            mode="markers",
            name="Out of stock",
            marker=dict(
                color="#ffc107",
                size=8,
                symbol="x",
            ),
            hovertemplate=(
                "Out of stock<br>"
                "%{x|%d %b %Y %H:%M}<br>"
                "<extra></extra>"
            ),
        ))

    # ── Layout ────────────────────────────────────────────────────────────────
    # Truncate long titles for chart display
    display_title = (
        product_title[:60] + "..." if len(product_title) > 60 else product_title
    )

    fig.update_layout(
        title=dict(
            text=f"Price History: {display_title}",
            font=dict(size=16, color="#333333"),
        ),
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="#f0f0f0",
            tickformat="%d %b %Y",
        ),
        yaxis=dict(
            title="Price (₹)",
            showgrid=True,
            gridcolor="#f0f0f0",
            tickprefix="₹",
            tickformat=",",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=20, t=80, b=60),
        height=400,
    )

    return fig


def build_price_stats(history: list, target_price: float) -> dict:
    """
    Compute summary statistics from price history.

    Returns dict with highest, lowest, average, total_records,
    times_below_target, and percentage_below_target.
    """
    if not history:
        return {}

    df = pd.DataFrame(history)
    in_stock = df[
        (df["availability"] == "in_stock") &
        (df["price"].notna())
    ]

    if in_stock.empty:
        return {}

    prices = in_stock["price"]
    below = in_stock[in_stock["price"] <= target_price]

    return {
        "highest": prices.max(),
        "lowest": prices.min(),
        "average": prices.mean(),
        "total_records": len(df),
        "in_stock_records": len(in_stock),
        "times_below_target": len(below),
        "percentage_below_target": (
            round(len(below) / len(in_stock) * 100, 1)
            if len(in_stock) > 0 else 0
        ),
    }