"""Streamlit view for Newsvendor (Single-Period) Model tool."""

from __future__ import annotations
import streamlit as st

from core.newsvendor import calculate_newsvendor, generate_newsvendor_profit_curve
from utils.visualizer import plot_newsvendor_profit_curve


def render_newsvendor_view():
    """Render the Newsvendor interactive tool."""
    st.header("📰 Newsvendor Model (Single-Period Inventory)")
    st.markdown(
        """
        The **Newsvendor Model** determines the profit-maximizing order quantity for single-period,
        perishable, or seasonal items with uncertain demand (e.g. fashion apparel, event merchandise, holiday goods).
        It balances the **cost of understocking** ($C_u$, lost profit) against the **cost of overstocking** ($C_o$, salvage loss).
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Price & Cost Economics")
        selling_price = st.number_input(
            "Selling Price per Unit (P) [$]",
            min_value=0.01,
            value=100.0,
            step=5.0,
            help="Revenue earned per unit sold during the selling season.",
        )
        purchase_cost = st.number_input(
            "Procurement Cost per Unit (C) [$]",
            min_value=0.01,
            value=40.0,
            step=5.0,
            help="Cost incurred to buy or produce each unit (must be < Selling Price).",
        )
        salvage_value = st.number_input(
            "Salvage / Clearance Value (V) [$]",
            min_value=0.0,
            value=15.0,
            step=5.0,
            help="Net recovery value per unsold leftover unit at end of season (must be < Procurement Cost).",
        )
        shortage_penalty = st.number_input(
            "Goodwill / Shortage Penalty (g) [$]",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Estimated customer goodwill loss or contractual penalty per lost sale (optional).",
        )

    with col2:
        st.subheader("Demand Distribution (Normal: μ, σ)")
        mean_demand = st.number_input(
            "Expected Demand (Mean μ) [units]",
            min_value=1.0,
            value=500.0,
            step=50.0,
            help="Average expected market demand for the period.",
        )
        std_demand = st.number_input(
            "Demand Standard Deviation (σ) [units]",
            min_value=0.1,
            value=100.0,
            step=10.0,
            help="Standard deviation measuring demand uncertainty.",
        )

    # Validation
    if purchase_cost <= salvage_value:
        st.error(f"Purchase cost (${purchase_cost:.2f}) must be strictly greater than salvage value (${salvage_value:.2f}).")
        return
    if selling_price <= purchase_cost:
        st.error(f"Selling price (${selling_price:.2f}) must be strictly greater than purchase cost (${purchase_cost:.2f}).")
        return

    try:
        results = calculate_newsvendor(
            selling_price=selling_price,
            purchase_cost=purchase_cost,
            salvage_value=salvage_value,
            mean_demand=mean_demand,
            std_demand=std_demand,
            shortage_penalty=shortage_penalty,
        )
    except Exception as e:
        st.error(f"Calculation Error: {str(e)}")
        return

    st.markdown("---")
    st.subheader("🎯 Optimal Order Decision & Margins")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cost of Underage (Cu)", f"${results['underage_cost']:,.2f}", "Profit Margin + Penalty")
    m2.metric("Cost of Overage (Co)", f"${results['overage_cost']:,.2f}", "Cost - Salvage")
    m3.metric("Critical Ratio (CR)", f"{results['critical_ratio']:.4f}", f"Target In-Stock = {results['critical_ratio']*100:.1f}%")
    m4.metric("Optimal Order (Q*)", f"{results['optimal_quantity']:,.1f} units", f"≈ {results['optimal_quantity_rounded']:,} units")

    # Financial and operational expectations
    st.markdown("### 📊 Expected Performance Breakdown")
    f1, f2, f3, f4 = st.columns(4)
    f1.info(f"**Expected Sales:**\n\n### {results['expected_sales']:,.1f}\nunits sold at full price")
    f2.info(f"**Expected Leftovers:**\n\n### {results['expected_leftover']:,.1f}\nunits salvaged at end of season")
    f3.info(f"**Expected Lost Sales:**\n\n### {results['expected_shortage']:,.1f}\nunmet demand units")
    f4.success(f"**Expected Profit:**\n\n### ${results['expected_profit']:,.2f}\nat optimal Q*")

    st.caption(
        f"💡 **Managerial Interpretation:** Because the margin of profit ($C_u = \${results['underage_cost']:.2f}) "
        f"{'exceeds' if results['underage_cost'] > results['overage_cost'] else 'is less than'} "
        f"the risk of leftover loss ($C_o = \${results['overage_cost']:.2f}), "
        f"the Critical Ratio is {results['critical_ratio']*100:.1f}%. "
        f"Therefore, it is optimal to order {'more than' if results['critical_ratio'] > 0.5 else 'less than'} "
        f"the average demand of {results['mean_demand']:.0f} units (optimal $Q^* = {results['optimal_quantity_rounded']:,}$ units)."
    )

    # Plot
    curve_data = generate_newsvendor_profit_curve(
        selling_price=selling_price,
        purchase_cost=purchase_cost,
        salvage_value=salvage_value,
        mean_demand=mean_demand,
        std_demand=std_demand,
        shortage_penalty=shortage_penalty,
    )
    fig = plot_newsvendor_profit_curve(
        q_values=curve_data["q_values"],
        profits=curve_data["expected_profits"],
        optimal_q=curve_data["optimal_q"],
        max_profit=curve_data["max_profit"],
    )
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📝 Academic Step-by-Step Formula Breakdown"):
        st.markdown(
            rf"""
            **1. Marginal Underage Cost ($C_u$):**
            $$C_u = P - C + g = \${results['selling_price']:.2f} - \${results['purchase_cost']:.2f} + \${results['shortage_penalty']:.2f} = \${results['underage_cost']:.2f}$$

            **2. Marginal Overage Cost ($C_o$):**
            $$C_o = C - V = \${results['purchase_cost']:.2f} - \${results['salvage_value']:.2f} = \${results['overage_cost']:.2f}$$

            **3. Critical Ratio (Critical Fractile $CR$):**
            $$CR = \frac{{C_u}}{{C_u + C_o}} = \frac{{{results['underage_cost']:.2f}}}{{{results['underage_cost']:.2f} + {results['overage_cost']:.2f}}} = {results['critical_ratio']:.4f}$$

            **4. Optimal Safety Factor ($z^*$):**
            $$z^* = \Phi^{{-1}}({results['critical_ratio']:.4f}) = {results['z_star']:.4f}$$

            **5. Optimal Order Quantity ($Q^*$):**
            $$Q^* = \mu + z^* \cdot \sigma = {results['mean_demand']:.1f} + ({results['z_star']:.4f} \times {results['std_demand']:.1f}) = {results['optimal_quantity']:.2f}\text{{ units}} \implies {results['optimal_quantity_rounded']}\text{{ units}}$$

            **6. Expected Value of Perfect Information ($EVPI$):**
            $$EVPI = \text{{Profit}}_{{\text{{perfect}}}} - E[\Pi(Q^*)] = \${results['expected_profit_perfect_info']:,.2f} - \${results['expected_profit']:,.2f} = \${results['evpi']:,.2f}$$
            """
        )
