"""Inventory Decision Agent - University Inventory Analytics.

Main application entry point orchestrating modular inventory decision tools.
"""

from __future__ import annotations
import streamlit as st

from ui.view_eoq import render_eoq_view
from ui.view_discount import render_quantity_discount_view
from ui.view_safety_stock import render_safety_stock_view
from ui.view_periodic import render_periodic_review_view
from ui.view_newsvendor import render_newsvendor_view
from ui.view_batch_upload import render_batch_upload_view


def render_home_view():
    """Render the dashboard landing page with course overview and decision matrix."""
    st.title("🎓 Inventory Decision Agent")
    st.markdown(
        """
        Welcome to the **Inventory Decision Agent**, an interactive decision-support application
        built for **University Inventory Analytics & Supply Chain Management**.

        This system operationalizes foundational operations research models to balance
        **procurement, holding, stockout, and ordering costs** across single-item and multi-item catalogs.
        """
    )

    st.markdown("---")
    st.subheader("🛠️ Available Inventory Analytics Capabilities")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            ### 1. 📦 Economic Order Quantity (EOQ)
            * **Demand Pattern:** Constant & deterministic.
            * **Decision:** Optimal batch size ($Q^*$) balancing fixed order costs ($S$) and holding costs ($H$).
            * **Includes:** Orders/year, cycle time, cost curves, and supplier MOQ sensitivity.
            """
        )
        st.markdown(
            """
            ### 2. 🏷️ Quantity Discount Analysis
            * **Decision:** Optimal all-units order quantity when suppliers offer volume price breaks.
            * **Includes:** Tier-by-tier unconstrained EOQ, feasibility adjustments, and net annual savings.
            """
        )

    with col2:
        st.markdown(
            """
            ### 3. 🛡️ Safety Stock & Reorder Point
            * **Demand Pattern:** Continuous review $(s, S)$ or $(R, Q)$ under uncertainty.
            * **Decision:** Reorder point ($ROP$) and safety buffer ($SS$) for target Cycle Service Level ($CSL$).
            * **Includes:** Stochastic demand, stochastic lead times, and normal distribution charts.
            """
        )
        st.markdown(
            """
            ### 4. 📅 Fixed-Period Review (P, S)
            * **Demand Pattern:** Periodic review at fixed intervals ($P$).
            * **Decision:** Target Order-Up-To Level ($OUL$) and replenishment sizing based on current stock position.
            * **Includes:** Protection period ($P+L$) analysis vs continuous review.
            """
        )

    with col3:
        st.markdown(
            """
            ### 5. 📰 Newsvendor Model
            * **Demand Pattern:** Single-period, perishable or seasonal items.
            * **Decision:** Stocking quantity ($Q^*$) based on underage ($C_u$) and overage ($C_o$) cost ratio.
            * **Includes:** Critical fractile, expected leftovers, expected lost sales, and EVPI.
            """
        )
        st.markdown(
            """
            ### 6. 📂 CSV File Upload (pandas)
            * **Capability:** Multi-SKU batch processing across product catalogs.
            * **Includes:** Downloadable CSV templates, schema validation, batch calculations, and CSV export.
            """
        )

    st.markdown("---")
    st.subheader("🧭 Quick Decision Guide: Which Model Should You Use?")
    
    st.markdown(
        """
        | Business Situation | Recommended Tool | Key Trade-off / Focus |
        | :--- | :--- | :--- |
        | Stable demand, repeated orders throughout year | **EOQ** | Fixed ordering cost vs. capital carrying cost |
        | Supplier offers tier-based discount pricing | **Quantity Discount** | Bulk purchase discounts vs. increased holding cost |
        | Continuous tracking, lead time uncertainty | **Safety Stock & ROP** | Buffer sizing against stockout probability |
        | Scheduled vendor reviews (e.g. weekly orders) | **Fixed-Period Review** | Synchronization vs. higher protection period ($P+L$) |
        | Seasonal, holiday, or perishable products | **Newsvendor Model** | Marginal cost of overstocking vs. understocking |
        | Bulk multi-item product catalogs | **CSV Upload (pandas)** | Catalog-wide batch optimization & reporting |
        | Multicriteria ABC classification (BAN 517) | **CSV Upload (pandas)** | 0.65 Sales ($) + 0.35 POS Hits weighted scoring |
        """
    )

    st.success(
        "✨ **BAN 517 Multicriteria Classification Active:** You can now classify inventory catalogs based on "
        "Sales ($) and POS Hits directly in the **CSV Upload & Batch (pandas)** section."
    )


def main():
    st.set_page_config(
        page_title="Inventory Decision Agent",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("📦 Inventory Agent")
    st.sidebar.caption("University Inventory Analytics")

    navigation_pages = {
        "🏠 Overview & Guide": render_home_view,
        "📦 Economic Order Quantity": render_eoq_view,
        "🏷️ Quantity Discount Analysis": render_quantity_discount_view,
        "🛡️ Safety Stock & ROP": render_safety_stock_view,
        "📅 Fixed-Period Review": render_periodic_review_view,
        "📰 Newsvendor Model": render_newsvendor_view,
        "📂 CSV Upload & Batch (pandas)": render_batch_upload_view,
    }

    selected_page = st.sidebar.radio(
        "Select Analytical Capability:",
        options=list(navigation_pages.keys()),
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **System Features:**
        - ✅ Standard Operations Formulas
        - ✅ Consistent Units & Validations
        - ✅ Interactive Plotly Analytics
        - ✅ Batch Processing via pandas
        """
    )

    # Route to selected view
    page_func = navigation_pages[selected_page]
    page_func()


if __name__ == "__main__":
    main()
