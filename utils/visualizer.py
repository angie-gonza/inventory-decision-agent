"""Interactive Plotly visualization generators for inventory analysis."""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def plot_eoq_curves(
    annual_demand: float,
    order_cost: float,
    holding_cost: float,
    eoq: float,
) -> Optional[Any]:
    """Generate an interactive Plotly chart of EOQ cost curves."""
    if not HAS_PLOTLY:
        return None

    min_q = max(1.0, eoq * 0.25)
    max_q = eoq * 2.2
    steps = 80
    step_size = (max_q - min_q) / (steps - 1)

    q_vals = [min_q + i * step_size for i in range(steps)]
    order_costs = [(annual_demand / q) * order_cost for q in q_vals]
    hold_costs = [(q / 2.0) * holding_cost for q in q_vals]
    total_costs = [o + h for o, h in zip(order_costs, hold_costs)]

    min_tc = math.sqrt(2.0 * annual_demand * order_cost * holding_cost)

    fig = go.Figure()

    # Ordering Cost curve
    fig.add_trace(go.Scatter(
        x=q_vals,
        y=order_costs,
        mode="lines",
        name="Annual Ordering Cost",
        line=dict(color="#EF4444", width=2, dash="dash"),
    ))

    # Holding Cost curve
    fig.add_trace(go.Scatter(
        x=q_vals,
        y=hold_costs,
        mode="lines",
        name="Annual Holding Cost",
        line=dict(color="#3B82F6", width=2, dash="dash"),
    ))

    # Total Variable Cost curve
    fig.add_trace(go.Scatter(
        x=q_vals,
        y=total_costs,
        mode="lines",
        name="Total Variable Inventory Cost",
        line=dict(color="#10B981", width=3),
    ))

    # Optimal EOQ Point
    fig.add_trace(go.Scatter(
        x=[eoq],
        y=[min_tc],
        mode="markers+text",
        name=f"Optimal EOQ ({round(eoq, 1)} units)",
        marker=dict(color="#F59E0B", size=12, symbol="star"),
        text=[f"EOQ = {round(eoq, 1)}<br>TIC = ${min_tc:,.2f}"],
        textposition="top center",
    ))

    fig.add_vline(x=eoq, line_width=1.5, line_dash="dot", line_color="#F59E0B")

    fig.update_layout(
        title="<b>EOQ Cost Trade-off: Ordering vs. Holding vs. Total Cost</b>",
        xaxis_title="Order Quantity (Q) [units]",
        yaxis_title="Annual Cost ($)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plot_quantity_discount_comparison(
    tier_evaluations: List[Dict[str, Any]],
    optimal_tier_id: int,
) -> Optional[Any]:
    """Generate a bar chart comparing total annual costs across quantity discount tiers."""
    if not HAS_PLOTLY:
        return None

    tier_labels = []
    ordering_costs = []
    holding_costs = []
    purchase_costs = []
    colors = []

    for ev in tier_evaluations:
        label = f"Tier {ev['tier_id']} (Q={round(ev['candidate_q'])})"
        tier_labels.append(label)
        if ev["is_valid"] and ev["annual_order_cost"] is not None:
            ordering_costs.append(ev["annual_order_cost"])
            holding_costs.append(ev["annual_holding_cost"])
            purchase_costs.append(ev["annual_purchase_cost"])
        else:
            ordering_costs.append(0)
            holding_costs.append(0)
            purchase_costs.append(0)

        colors.append("#10B981" if ev["tier_id"] == optimal_tier_id else "#94A3B8")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=tier_labels,
        y=purchase_costs,
        name="Purchase Cost ($)",
        marker_color="#6366F1",
    ))
    fig.add_trace(go.Bar(
        x=tier_labels,
        y=holding_costs,
        name="Holding Cost ($)",
        marker_color="#3B82F6",
    ))
    fig.add_trace(go.Bar(
        x=tier_labels,
        y=ordering_costs,
        name="Ordering Cost ($)",
        marker_color="#F97316",
    ))

    fig.update_layout(
        barmode="stack",
        title="<b>Total Annual Cost Breakdown Across Price Tiers (Green Star = Optimal)</b>",
        xaxis_title="Discount Tier & Candidate Batch Size",
        yaxis_title="Total Annual Cost ($)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plot_safety_stock_distribution(
    mean_ltd: float,
    std_ltd: float,
    safety_stock: float,
    reorder_point: float,
    service_level: float,
) -> Optional[Any]:
    """Generate a bell curve visualization of lead time demand, safety stock, and ROP."""
    if not HAS_PLOTLY or std_ltd <= 0:
        return None

    min_x = max(0.0, mean_ltd - 3.8 * std_ltd)
    max_x = mean_ltd + 4.2 * std_ltd
    steps = 150
    step = (max_x - min_x) / (steps - 1)
    x_vals = [min_x + i * step for i in range(steps)]

    # Standard normal density formula
    def pdf(x):
        z = (x - mean_ltd) / std_ltd
        return (1.0 / (std_ltd * math.sqrt(2.0 * math.pi))) * math.exp(-0.5 * z * z)

    y_vals = [pdf(x) for x in x_vals]

    fig = go.Figure()

    # Full distribution curve
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="lines",
        name="Lead Time Demand Distribution",
        line=dict(color="#3B82F6", width=2.5),
    ))

    # Shaded in-stock region up to ROP
    x_fill = [x for x in x_vals if x <= reorder_point]
    y_fill = [pdf(x) for x in x_fill]
    if x_fill:
        fig.add_trace(go.Scatter(
            x=x_fill + [x_fill[-1], x_fill[0]],
            y=y_fill + [0, 0],
            fill="toself",
            fillcolor="rgba(16, 185, 129, 0.25)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"In-Stock Probability ({service_level*100:.1f}%)",
        ))

    # Shaded stockout tail above ROP
    x_stockout = [x for x in x_vals if x >= reorder_point]
    y_stockout = [pdf(x) for x in x_stockout]
    if x_stockout:
        fig.add_trace(go.Scatter(
            x=x_stockout + [x_stockout[-1], x_stockout[0]],
            y=y_stockout + [0, 0],
            fill="toself",
            fillcolor="rgba(239, 68, 68, 0.35)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"Stockout Risk ({(1.0 - service_level)*100:.1f}%)",
        ))

    # Expected Demand vertical line
    fig.add_vline(x=mean_ltd, line_width=2, line_dash="dash", line_color="#6B7280",
                  annotation_text=f"E[LTD] = {mean_ltd:.1f}", annotation_position="top left")

    # Reorder Point vertical line
    fig.add_vline(x=reorder_point, line_width=2.5, line_color="#EF4444",
                  annotation_text=f"ROP = {reorder_point:.1f} (SS = {safety_stock:.1f})", annotation_position="top right")

    fig.update_layout(
        title="<b>Lead Time Demand Distribution & Safety Stock Buffer</b>",
        xaxis_title="Demand During Replenishment Lead Time (Units)",
        yaxis_title="Probability Density",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plot_periodic_review_waterfall(
    on_hand: float,
    on_order: float,
    backorders: float,
    order_up_to_level: float,
    order_quantity: float,
) -> Optional[Any]:
    """Generate a visual comparison of current inventory position vs. Target Order-Up-To Level."""
    if not HAS_PLOTLY:
        return None

    inventory_position = on_hand + on_order - backorders

    categories = [
        "On-Hand",
        "On-Order (+)",
        "Backorders (-)",
        "Inventory Position",
        "Recommended Order",
        "Order-Up-To Target (S)",
    ]
    values = [
        on_hand,
        on_order,
        -backorders,
        inventory_position,
        order_quantity,
        order_up_to_level,
    ]
    colors = [
        "#3B82F6",
        "#60A5FA",
        "#EF4444",
        "#6366F1",
        "#F59E0B",
        "#10B981",
    ]

    fig = go.Figure(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=[f"{v:.0f}" for v in values],
        textposition="outside",
    ))

    fig.update_layout(
        title="<b>Periodic Review Inventory Position vs. Target Level (S)</b>",
        xaxis_title="Inventory Metric",
        yaxis_title="Units",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plot_newsvendor_profit_curve(
    q_values: List[float],
    profits: List[float],
    optimal_q: float,
    max_profit: float,
) -> Optional[Any]:
    """Generate an expected profit curve for the Newsvendor problem."""
    if not HAS_PLOTLY:
        return None

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=q_values,
        y=profits,
        mode="lines",
        name="Expected Profit ($)",
        line=dict(color="#10B981", width=3),
    ))

    fig.add_trace(go.Scatter(
        x=[optimal_q],
        y=[max_profit],
        mode="markers+text",
        name=f"Optimal Q* ({round(optimal_q, 1)})",
        marker=dict(color="#F59E0B", size=12, symbol="star"),
        text=[f"Q* = {optimal_q:.1f}<br>E[Profit] = ${max_profit:,.2f}"],
        textposition="top center",
    ))

    fig.add_vline(x=optimal_q, line_width=1.5, line_dash="dot", line_color="#F59E0B")

    fig.update_layout(
        title="<b>Newsvendor Expected Profit Curve vs. Order Quantity</b>",
        xaxis_title="Order Quantity (Q)",
        yaxis_title="Expected Profit ($)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plot_classification_distribution(summary_df: Any) -> Optional[Any]:
    """Generate a grouped bar chart showing % of Items vs % of Total Sales across Final Classes A, B, C, D."""
    if not HAS_PLOTLY or summary_df is None or len(summary_df) == 0:
        return None

    classes = summary_df["Final Class"].tolist()
    pct_items = summary_df["% of Items"].tolist()
    pct_sales = summary_df["% of Total Sales"].tolist()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=classes,
        y=pct_items,
        name="% of Total Catalog Items",
        marker_color="#3B82F6",
        text=[f"{v:.1f}%" for v in pct_items],
        textposition="outside",
    ))

    fig.add_trace(go.Bar(
        x=classes,
        y=pct_sales,
        name="% of Total Dollar Sales",
        marker_color="#10B981",
        text=[f"{v:.1f}%" for v in pct_sales],
        textposition="outside",
    ))

    fig.update_layout(
        barmode="group",
        title="<b>BAN 517 Multicriteria Pareto Distribution: Items vs. Sales Contribution</b>",
        xaxis_title="Final Inventory Class",
        yaxis_title="Percentage (%)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig
