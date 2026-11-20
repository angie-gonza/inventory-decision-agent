"""Streamlit view for Safety Stock and Reorder Point (ROP) tool."""

from __future__ import annotations
import streamlit as st

from core.safety_stock_rop import calculate_safety_stock_rop, LTDUncertaintyMode
from utils.visualizer import plot_safety_stock_distribution
from utils.validators import validate_range


def render_safety_stock_view():
    """Render the Safety Stock and Reorder Point interactive tool."""
    st.header("🛡️ Safety Stock & Reorder Point (Continuous Review)")
    st.markdown(
        """
        In a continuous review policy $(R, Q)$ or $(s, S)$, inventory is monitored continuously.
        Whenever the inventory position drops to or below the **Reorder Point (ROP)**, a replenishment
        order is placed. Safety Stock provides a statistical buffer against stockouts during the replenishment lead time.
        """
    )

    time_unit = st.selectbox("Operating Time Unit for Rates & Lead Time:", ["Days", "Weeks", "Months"], index=0)

    mode_options = {
        "Stochastic Demand with Constant Lead Time": LTDUncertaintyMode.DEMAND_ONLY,
        "Constant Demand with Stochastic Lead Time": LTDUncertaintyMode.LEAD_TIME_ONLY,
        "Both Demand and Lead Time are Stochastic (Independent)": LTDUncertaintyMode.BOTH,
    }

    selected_mode_label = st.radio(
        "Select Uncertainty Scenario:",
        options=list(mode_options.keys()),
        index=0,
    )
    chosen_mode = mode_options[selected_mode_label]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Demand Parameters (per {time_unit[:-1]})")
        mean_demand = st.number_input(
            f"Mean Demand (μ_d) [units/{time_unit[:-1].lower()}]",
            min_value=0.1,
            value=50.0,
            step=5.0,
            help="Average expected customer demand per period.",
        )

        if chosen_mode in [LTDUncertaintyMode.DEMAND_ONLY, LTDUncertaintyMode.BOTH]:
            std_demand = st.number_input(
                f"Demand Standard Deviation (σ_d) [units/{time_unit[:-1].lower()}]",
                min_value=0.0,
                value=10.0,
                step=1.0,
                help="Standard deviation measuring demand variability per period.",
            )
        else:
            std_demand = 0.0
            st.info("ℹ️ Demand is assumed constant (deterministic).")

    with col2:
        st.subheader(f"Lead Time Parameters ({time_unit})")
        mean_lead_time = st.number_input(
            f"Mean Lead Time (L or μ_L) [{time_unit.lower()}]",
            min_value=0.1,
            value=6.0,
            step=1.0,
            help="Average time required between placing an order and receiving delivery.",
        )

        if chosen_mode in [LTDUncertaintyMode.LEAD_TIME_ONLY, LTDUncertaintyMode.BOTH]:
            std_lead_time = st.number_input(
                f"Lead Time Standard Deviation (σ_L) [{time_unit.lower()}]",
                min_value=0.0,
                value=1.5,
                step=0.5,
                help="Standard deviation measuring supplier delivery variability.",
            )
        else:
            std_lead_time = 0.0
            st.info("ℹ️ Lead time is assumed constant (deterministic).")

    st.subheader("🎯 Service Level Target")
    csl_col1, csl_col2 = st.columns([2, 1])
    with csl_col1:
        service_level_pct = st.slider(
            "Cycle Service Level (CSL) [%]",
            min_value=50.0,
            max_value=99.9,
            value=95.0,
            step=0.5,
            help="Probability of NOT running out of stock during the replenishment lead time cycle.",
        )
    with csl_col2:
        csl_decimal = service_level_pct / 100.0
        st.metric("Target In-Stock Probability", f"{csl_decimal*100:.1f}%", f"Stockout Risk = {(1.0-csl_decimal)*100:.1f}%")

    try:
        results = calculate_safety_stock_rop(
            service_level=csl_decimal,
            mode=chosen_mode,
            mean_demand=mean_demand,
            std_demand=std_demand,
            mean_lead_time=mean_lead_time,
            std_lead_time=std_lead_time,
        )
    except Exception as e:
        st.error(f"Calculation Error: {str(e)}")
        return

    st.markdown("---")
    st.subheader("Decision Results & Inventory Policy")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Safety Stock (SS)", f"{results['safety_stock']:,.1f} units", f"Recommend: {results['safety_stock_rounded']:,}")
    m2.metric("Reorder Point (ROP)", f"{results['reorder_point']:,.1f} units", f"Order when IP ≤ {results['reorder_point_rounded']:,}")
    m3.metric("Expected Demand in LT", f"{results['mean_lead_time_demand']:,.1f} units", "μ_d × μ_L")
    m4.metric("Safety Factor (z)", f"{results['z_score']:.3f}", f"for {service_level_pct}% CSL")

    st.success(
        f"**Decision Recommendation:** Whenever your inventory position (On-Hand + On-Order - Backorders) drops to "
        f"**{results['reorder_point_rounded']:,} units**, place a replenishment order. "
        f"The buffer of **{results['safety_stock_rounded']:,} units** protects against demand spikes with {service_level_pct}% confidence."
    )

    # Plot
    fig = plot_safety_stock_distribution(
        mean_ltd=results["mean_lead_time_demand"],
        std_ltd=results["std_lead_time_demand"],
        safety_stock=results["safety_stock"],
        reorder_point=results["reorder_point"],
        service_level=csl_decimal,
    )
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📝 Academic Step-by-Step Formula Breakdown"):
        st.markdown(
            rf"""
            **Scenario:** {results['case_description']}

            **1. Expected Demand During Lead Time ($\mu_L$):**
            $$\mu_L = \mu_d \times \mu_{{\text{{LT}}}} = {results['mean_demand']:.2f} \times {results['mean_lead_time']:.2f} = {results['mean_lead_time_demand']:.2f}\text{{ units}}$$

            **2. Standard Deviation of Demand During Lead Time ($\sigma_L$):**
            $$\text{{Formula: }} {results['formula_text']}$$
            $$\sigma_L = {results['std_lead_time_demand']:.2f}\text{{ units}}$$

            **3. Safety Factor ($z$ for CSL = {results['service_level']*100:.1f}%):**
            $$z = \Phi^{{-1}}({results['service_level']:.4f}) = {results['z_score']:.3f}$$

            **4. Safety Stock ($SS$):**
            $$SS = z \times \sigma_L = {results['z_score']:.3f} \times {results['std_lead_time_demand']:.2f} = {results['safety_stock']:.2f}\text{{ units}} \implies \lceil {results['safety_stock']:.2f} \rceil = {results['safety_stock_rounded']}\text{{ units}}$$

            **5. Reorder Point ($ROP$):**
            $$ROP = \mu_L + SS = {results['mean_lead_time_demand']:.2f} + {results['safety_stock']:.2f} = {results['reorder_point']:.2f}\text{{ units}} \implies \lceil {results['reorder_point']:.2f} \rceil = {results['reorder_point_rounded']}\text{{ units}}$$
            """
        )
