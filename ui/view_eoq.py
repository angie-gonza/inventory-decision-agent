"""Streamlit view for Economic Order Quantity (EOQ) tool."""

from __future__ import annotations
import streamlit as st

from core.eoq import calculate_eoq, calculate_eoq_sensitivity
from utils.visualizer import plot_eoq_curves
from utils.validators import validate_positive


def render_eoq_view():
    """Render the Economic Order Quantity interactive tool."""
    st.header("📦 Economic Order Quantity (EOQ)")
    st.markdown(
        """
        The **Economic Order Quantity** finds the optimal replenishment batch size that minimizes
        the sum of fixed ordering costs and inventory holding costs under constant, deterministic demand.
        """
    )

    col_in1, col_in2 = st.columns([1, 1])

    with col_in1:
        st.subheader("Input Parameters")
        annual_demand = st.number_input(
            "Annual Demand (D) [units/year]",
            min_value=1.0,
            value=10000.0,
            step=500.0,
            help="Total annual customer demand in units.",
        )
        order_cost = st.number_input(
            "Order / Setup Cost (S) [$/order]",
            min_value=0.01,
            value=50.0,
            step=5.0,
            help="Fixed administrative and shipping cost incurred every time an order is placed.",
        )
        unit_cost = st.number_input(
            "Unit Purchase Cost (C) [$/unit]",
            min_value=0.01,
            value=20.0,
            step=1.0,
            help="Acquisition price per unit paid to the supplier.",
        )

    with col_in2:
        st.subheader("Holding Cost Specification")
        holding_mode = st.radio(
            "Define holding cost by:",
            options=["Holding Rate (h as % of unit cost)", "Fixed Cost per Unit per Year (H)"],
            index=0,
        )

        if holding_mode.startswith("Holding Rate"):
            holding_rate_pct = st.number_input(
                "Annual Holding Rate (h) [%]",
                min_value=0.1,
                max_value=100.0,
                value=20.0,
                step=1.0,
                help="Annual carrying cost as a percentage of unit cost (typically 15% - 35%).",
            )
            h_rate = holding_rate_pct / 100.0
            h_unit = None
        else:
            h_unit = st.number_input(
                "Holding Cost per Unit (H) [$/unit/year]",
                min_value=0.01,
                value=4.0,
                step=0.5,
                help="Direct cost to store and insure one unit for one year.",
            )
            h_rate = None

        working_days = st.number_input(
            "Operating Days per Year",
            min_value=100,
            max_value=365,
            value=250,
            step=10,
            help="Number of business operating days used to calculate order cycle time in days.",
        )

    # Validation
    val_ok, err_msg = validate_positive("Annual Demand", annual_demand)
    if not val_ok:
        st.error(err_msg)
        return

    try:
        results = calculate_eoq(
            annual_demand=annual_demand,
            order_cost=order_cost,
            unit_cost=unit_cost,
            holding_cost_rate=h_rate,
            holding_cost_per_unit=h_unit,
            working_days_per_year=int(working_days),
        )
    except Exception as e:
        st.error(f"Calculation Error: {str(e)}")
        return

    st.markdown("---")
    st.subheader("Key Inventory Decisions & Metrics")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Optimal Batch Size (EOQ)", f"{results['eoq']:,.1f} units", f"≈ {results['eoq_rounded']:,} units")
    m2.metric("Orders per Year", f"{results['orders_per_year']:.2f} orders", "replenishment cycles")
    m3.metric("Cycle Interval", f"{results['cycle_time_days']:.1f} days", f"{results['cycle_time_years']*12:.1f} months")
    m4.metric("Total Variable Cost", f"${results['total_variable_cost']:,.2f}", "AOC + AHC")

    # Cost breakdown table
    st.markdown("### 📊 Annual Cost Summary")
    c1, c2, c3 = st.columns(3)
    c1.info(f"**Annual Ordering Cost (AOC):**\n\n### ${results['annual_ordering_cost']:,.2f}\n*(D / Q) × S*")
    c2.info(f"**Annual Holding Cost (AHC):**\n\n### ${results['annual_holding_cost']:,.2f}\n*(Q / 2) × H*")
    c3.success(f"**Total Annual Cost (TC):**\n\n### ${results['total_annual_cost']:,.2f}\n*AOC + AHC + (D × C)*")

    # Theoretical Note
    st.caption("💡 *Notice that at optimal EOQ, Annual Ordering Cost exactly equals Annual Holding Cost.*")

    # Plot
    fig = plot_eoq_curves(
        annual_demand=results["annual_demand"],
        order_cost=results["order_cost"],
        holding_cost=results["holding_cost_per_unit"],
        eoq=results["eoq"],
    )
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    # Formula walkthrough
    with st.expander("📝 Academic Step-by-Step Formula Walkthrough"):
        st.markdown(
            rf"""
            **1. Holding Cost per Unit per Year ($H$):**
            $$H = h \times C = {results['holding_cost_rate']:.4f} \times \${results['unit_cost']:.2f} = \${results['holding_cost_per_unit']:.2f}\text{{ /unit/year}}$$

            **2. Economic Order Quantity ($Q^*$):**
            $$EOQ = \sqrt{{\frac{{2 \cdot D \cdot S}}{{H}}}} = \sqrt{{\frac{{2 \times {results['annual_demand']:,.0f} \times {results['order_cost']:,.2f}}}{{{results['holding_cost_per_unit']:.2f}}}}} = {results['eoq']:.2f}\text{{ units}}$$

            **3. Order Frequency ($N$):**
            $$N = \frac{{D}}{{Q^*}} = \frac{{{results['annual_demand']:,.0f}}}{{{results['eoq']:.2f}}} = {results['orders_per_year']:.2f}\text{{ orders/year}}$$

            **4. Cycle Time ($T$):**
            $$T = \frac{{Q^*}}{{D}} \times \text{{Days}} = \frac{{{results['eoq']:.2f}}}{{{results['annual_demand']:,.0f}}} \times {results['working_days_per_year']} = {results['cycle_time_days']:.1f}\text{{ days}}$$

            **5. Total Annual Inventory Cost ($TC$):**
            $$TC = \left(\frac{{D}}{{Q}}\right)S + \left(\frac{{Q}}{{2}}\right)H + (D \times C) = \${results['annual_ordering_cost']:,.2f} + \${results['annual_holding_cost']:,.2f} + \${results['annual_purchasing_cost']:,.2f} = \${results['total_annual_cost']:,.2f}$$
            """
        )

    # Sensitivity / Non-Optimal Batch Size Exploration
    with st.expander("🔍 Order Batch Sensitivity & Supplier MOQ Analysis"):
        st.markdown(
            """
            In practice, suppliers often enforce a **Minimum Order Quantity (MOQ)** or container pack size.
            Test an alternative batch size $Q$ to see the economic penalty:
            """
        )
        test_q = st.number_input(
            "Test Batch Size (e.g. MOQ or Container Size) [units]",
            min_value=1.0,
            value=float(results["eoq_rounded"]),
            step=50.0,
        )
        sens = calculate_eoq_sensitivity(
            annual_demand=results["annual_demand"],
            order_cost=results["order_cost"],
            holding_cost_per_unit=results["holding_cost_per_unit"],
            actual_q=test_q,
        )
        s_col1, s_col2, s_col3 = st.columns(3)
        s_col1.metric("Alternative Variable Cost", f"${sens['actual_tic']:,.2f}")
        s_col2.metric("Annual Cost Increase", f"${sens['cost_difference']:,.2f}")
        s_col3.metric("Cost Penalty", f"{sens['percentage_penalty']:.2f}%")
