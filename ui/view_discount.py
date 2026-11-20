"""Streamlit view for Quantity Discount Analysis tool."""

from __future__ import annotations
import pandas as pd
import streamlit as st

from core.quantity_discount import calculate_quantity_discount
from utils.visualizer import plot_quantity_discount_comparison
from utils.validators import validate_positive


def render_quantity_discount_view():
    """Render the Quantity Discount Analysis interactive tool."""
    st.header("🏷️ Quantity Discount Analysis (All-Units Discount)")
    st.markdown(
        """
        Suppliers often offer lower unit prices for higher purchase order volumes.
        This tool determines whether purchasing larger quantities to qualify for price breaks
        is financially justified by comparing purchase price savings against increased inventory holding costs.
        """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        annual_demand = st.number_input(
            "Annual Demand (D) [units/year]",
            min_value=1.0,
            value=8000.0,
            step=500.0,
            help="Total annual demand in units.",
        )
    with col2:
        order_cost = st.number_input(
            "Order / Setup Cost (S) [$/order]",
            min_value=0.01,
            value=60.0,
            step=5.0,
            help="Cost incurred to place each purchase order.",
        )
    with col3:
        holding_rate_pct = st.number_input(
            "Holding Rate (h) [% of unit price/yr]",
            min_value=0.1,
            max_value=100.0,
            value=20.0,
            step=1.0,
            help="Annual cost to hold one dollar's worth of inventory.",
        )

    st.subheader("📋 Supplier Price Break Schedule")
    st.markdown(
        "Define the quantity brackets and the corresponding unit prices. Leave `max_qty` empty or enter `None` for the highest tier."
    )

    default_tiers = [
        {"min_qty": 0, "max_qty": 999, "unit_price": 25.0},
        {"min_qty": 1000, "max_qty": 2499, "unit_price": 23.50},
        {"min_qty": 2500, "max_qty": None, "unit_price": 22.00},
    ]

    edited_df = st.data_editor(
        pd.DataFrame(default_tiers),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "min_qty": st.column_config.NumberColumn("Min Quantity (q_min)", min_value=0, required=True),
            "max_qty": st.column_config.NumberColumn("Max Quantity (q_max)", min_value=1, required=False),
            "unit_price": st.column_config.NumberColumn("Unit Price ($)", min_value=0.01, format="$%.2f", required=True),
        },
    )

    tiers_data = edited_df.to_dict(orient="records")

    try:
        results = calculate_quantity_discount(
            annual_demand=annual_demand,
            order_cost=order_cost,
            holding_cost_rate=holding_rate_pct / 100.0,
            price_tiers=tiers_data,
        )
    except Exception as e:
        st.error(f"Configuration / Calculation Error: {str(e)}")
        return

    st.markdown("---")
    st.subheader("💡 Optimal Procurement Recommendation")

    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    r_col1.metric("Recommended Tier", f"Tier {results['optimal_tier_id']}")
    r_col2.metric("Optimal Order Batch (Q*)", f"{results['optimal_quantity']:,.0f} units")
    r_col3.metric("Unit Price at Q*", f"${results['optimal_unit_price']:.2f}")
    r_col4.metric(
        "Min Total Annual Cost",
        f"${results['min_total_annual_cost']:,.2f}",
        f"Save ${results['total_savings']:,.2f} vs Base",
    )

    # Detailed comparison table
    st.markdown("### 📊 Tier-by-Tier Economic Comparison")
    table_rows = []
    for ev in results["tier_evaluations"]:
        max_str = f"{ev['max_qty']:,}" if ev["max_qty"] != float("inf") else "∞"
        table_rows.append({
            "Tier": f"Tier {ev['tier_id']}",
            "Bracket Range": f"{ev['min_qty']:,} – {max_str}",
            "Price ($)": f"${ev['unit_price']:.2f}",
            "Unconstrained EOQ": f"{ev['calculated_eoq']:,.1f}",
            "Candidate Q": f"{ev['candidate_q']:,.0f}",
            "Feasibility Status": ev["status"],
            "Annual Order Cost": f"${ev['annual_order_cost']:,.2f}" if ev["annual_order_cost"] else "N/A",
            "Annual Holding Cost": f"${ev['annual_holding_cost']:,.2f}" if ev["annual_holding_cost"] else "N/A",
            "Annual Purchase Cost": f"${ev['annual_purchase_cost']:,.2f}" if ev["annual_purchase_cost"] else "N/A",
            "Total Annual Cost": f"${ev['total_annual_cost']:,.2f}" if ev["total_annual_cost"] else "N/A",
            "Savings vs. Base ($)": f"${ev['savings_vs_base']:,.2f}" if ev.get("savings_vs_base") is not None else "$0.00",
            "Savings (%)": f"{ev['pct_savings_vs_base']:.2f}%" if ev.get("pct_savings_vs_base") is not None else "0.00%",
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    # Visualization
    fig = plot_quantity_discount_comparison(results["tier_evaluations"], results["optimal_tier_id"])
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📝 Academic Methodology: How the All-Units Discount Model Works"):
        st.markdown(
            rf"""
            **Step 1: Calculate Unconstrained EOQ for Each Price Tier ($i$):**
            $$EOQ_i = \sqrt{{\frac{{2 \cdot D \cdot S}}{{h \cdot C_i}}}}$$

            **Step 2: Feasibility and Candidate Quantity Selection:**
            * If $EOQ_i$ falls within the tier's quantity range $[q_i, q_{{i+1}})$, it is **feasible at EOQ** $\implies Q_i^* = EOQ_i$.
            * If $EOQ_i < q_i$, ordering at $EOQ_i$ would not qualify for price $C_i$. We adjust to the lower price-break boundary: $Q_i^* = q_i$.
            * If $EOQ_i \ge q_{{i+1}}$, this tier is dominated by a higher tier offering an even lower unit price.

            **Step 3: Total Annual Cost Evaluation:**
            $$TC(Q_i^*) = \left(\frac{{D}}{{Q_i^*}}\right)S + \left(\frac{{Q_i^*}}{{2}}\right)(h \cdot C_i) + (D \cdot C_i)$$

            **Step 4: Decision Rule:**
            Select the candidate quantity $Q^*$ that yields the minimum $TC(Q_i^*)$ across all valid tiers.
            """
        )
