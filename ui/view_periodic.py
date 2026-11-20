"""Streamlit view for Fixed-Period Review (Periodic Review) tool."""

from __future__ import annotations
import streamlit as st

from core.periodic_review import calculate_periodic_review
from utils.visualizer import plot_periodic_review_waterfall


def render_periodic_review_view():
    """Render the Fixed-Period Review interactive tool."""
    st.header("📅 Fixed-Period Review (Periodic Policy: P, S)")
    st.markdown(
        """
        In a **Fixed-Period Review Policy** $(P, S)$ (or $(T, M)$), inventory is checked only at regular
        intervals of length **$P$** (e.g. every Monday). An order is placed to bring the
        **Inventory Position** up to a target **Order-Up-To Level ($S$)**.
        
        Because orders only occur every $P$ intervals, the safety stock must protect across the entire
        **Protection Interval ($P + L$)**, requiring more safety stock than continuous review.
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Time Horizons & Demand")
        review_period = st.number_input(
            "Review Period (P) [days]",
            min_value=1.0,
            value=7.0,
            step=1.0,
            help="Interval between successive inventory reviews and order placements.",
        )
        lead_time = st.number_input(
            "Lead Time (L) [days]",
            min_value=0.0,
            value=5.0,
            step=1.0,
            help="Replenishment lead time between order placement and receipt.",
        )
        mean_demand = st.number_input(
            "Mean Daily Demand (μ_d) [units/day]",
            min_value=0.1,
            value=30.0,
            step=5.0,
            help="Expected daily demand.",
        )
        std_demand = st.number_input(
            "Daily Demand Std Dev (σ_d) [units/day]",
            min_value=0.0,
            value=6.0,
            step=1.0,
            help="Daily demand standard deviation.",
        )

    with col2:
        st.subheader("Current Stock & Service Level")
        service_level_pct = st.slider(
            "Cycle Service Level (CSL) [%]",
            min_value=50.0,
            max_value=99.9,
            value=95.0,
            step=0.5,
            help="Target probability of avoiding stockout over the entire protection period (P + L).",
        )
        on_hand = st.number_input(
            "Current On-Hand Stock (I_hand) [units]",
            min_value=0.0,
            value=110.0,
            step=10.0,
            help="Physical stock currently in the warehouse.",
        )
        on_order = st.number_input(
            "On-Order / In-Transit (I_transit) [units]",
            min_value=0.0,
            value=60.0,
            step=10.0,
            help="Replenishment orders already placed but not yet received.",
        )
        backorders = st.number_input(
            "Backorders / Unfilled Orders (B) [units]",
            min_value=0.0,
            value=0.0,
            step=5.0,
            help="Unfulfilled demand committed to customers.",
        )

    try:
        results = calculate_periodic_review(
            review_period=review_period,
            lead_time=lead_time,
            mean_demand_per_period=mean_demand,
            std_demand_per_period=std_demand,
            service_level=service_level_pct / 100.0,
            on_hand_inventory=on_hand,
            on_order_inventory=on_order,
            backorders=backorders,
        )
    except Exception as e:
        st.error(f"Calculation Error: {str(e)}")
        return

    st.markdown("---")
    st.subheader("🎯 Replenishment Decision & Targets")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Protection Horizon (P + L)", f"{results['protection_interval']:.0f} days", f"P={results['review_period']}d + L={results['lead_time']}d")
    k2.metric("Target Level (S / OUL)", f"{results['order_up_to_level']:,.1f} units", f"Target: {results['order_up_to_level_rounded']:,}")
    k3.metric("Current Inventory Position", f"{results['inventory_position']:,.0f} units", "On-Hand + On-Order - Backorders")
    k4.metric("Recommended Order Quantity", f"{results['order_quantity_rounded']:,} units", f"Raw: {results['order_quantity']:.1f}")

    if results["order_quantity"] > 0:
        st.success(
            f"🛒 **Action:** Place a replenishment purchase order for **{results['order_quantity_rounded']:,} units** today "
            f"to bring your inventory position back up to the target Order-Up-To Level of **{results['order_up_to_level_rounded']:,} units**."
        )
    else:
        st.warning(
            f"⏸️ **Action:** No replenishment order needed today. Current inventory position ({results['inventory_position']:.0f} units) "
            f"meets or exceeds the target Order-Up-To Level ({results['order_up_to_level_rounded']:,} units)."
        )

    # Visualization
    fig = plot_periodic_review_waterfall(
        on_hand=results["on_hand_inventory"],
        on_order=results["on_order_inventory"],
        backorders=results["backorders"],
        order_up_to_level=results["order_up_to_level"],
        order_quantity=results["order_quantity"],
    )
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    # Comparison note with continuous review
    st.markdown("### ⚖️ Comparison with Continuous Review")
    comp_c1, comp_c2 = st.columns(2)
    comp_c1.info(
        f"**Periodic Safety Stock ($SS_{{P+L}}$):**\n\n"
        f"### {results['safety_stock_periodic']:.1f} units\n"
        f"Protects over $P + L = {results['protection_interval']:.0f}$ days."
    )
    comp_c2.info(
        f"**Continuous Safety Stock ($SS_{{L}}$):**\n\n"
        f"### {results['continuous_safety_stock']:.1f} units\n"
        f"Protects only over lead time $L = {results['lead_time']:.0f}$ days."
    )
    st.caption(
        f"📌 *Periodic review requires **+{results['safety_stock_increase_pct']:.1f}% more safety stock** "
        f"because inventory cannot be replenished until the next review cycle arrives.*"
    )

    with st.expander("📝 Academic Step-by-Step Formula Breakdown"):
        st.markdown(
            rf"""
            **1. Protection Interval ($T_{{\text{{prot}}}}$):**
            $$T_{{\text{{prot}}}} = P + L = {results['review_period']} + {results['lead_time']} = {results['protection_interval']:.1f}\text{{ days}}$$

            **2. Expected Demand over Protection Interval ($\mu_{{P+L}}$):**
            $$\mu_{{P+L}} = \mu_d \times (P + L) = {results['mean_demand_per_period']:.2f} \times {results['protection_interval']:.1f} = {results['mean_protection_demand']:.2f}\text{{ units}}$$

            **3. Standard Deviation over Protection Interval ($\sigma_{{P+L}}$):**
            $$\sigma_{{P+L}} = \sigma_d \sqrt{{P + L}} = {results['std_demand_per_period']:.2f} \times \sqrt{{{results['protection_interval']:.1f}}} = {results['std_protection_demand']:.2f}\text{{ units}}$$

            **4. Safety Stock ($SS$):**
            $$SS = z \times \sigma_{{P+L}} = {results['z_score']:.3f} \times {results['std_protection_demand']:.2f} = {results['safety_stock_periodic']:.2f}\text{{ units}}$$

            **5. Order-Up-To Level ($S$ / OUL):**
            $$S = \mu_{{P+L}} + SS = {results['mean_protection_demand']:.2f} + {results['safety_stock_periodic']:.2f} = {results['order_up_to_level']:.2f}\text{{ units}} \implies \lceil {results['order_up_to_level']:.2f} \rceil = {results['order_up_to_level_rounded']}\text{{ units}}$$

            **6. Inventory Position ($IP$):**
            $$IP = \text{{On-Hand}} + \text{{On-Order}} - \text{{Backorders}} = {results['on_hand_inventory']:.0f} + {results['on_order_inventory']:.0f} - {results['backorders']:.0f} = {results['inventory_position']:.0f}\text{{ units}}$$

            **7. Recommended Order Quantity ($Q$):**
            $$Q = \max(0, S - IP) = \max(0, {results['order_up_to_level_rounded']} - {results['inventory_position']:.0f}) = {results['order_quantity_rounded']}\text{{ units}}$$
            """
        )
