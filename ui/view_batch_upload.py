"""Streamlit view for CSV File Upload and Batch Processing using pandas."""

from __future__ import annotations
import io
import pandas as pd
import streamlit as st

from utils.data_loader import generate_sample_csv, process_batch_csv, SAMPLE_TEMPLATES
from utils.visualizer import plot_classification_distribution


def render_batch_upload_view():
    """Render the CSV File Upload and Batch Processing tool."""
    st.header("📂 CSV File Upload & Batch Processing (pandas)")
    st.markdown(
        """
        Upload multi-item inventory data in CSV format to calculate inventory policies
        and multicriteria classifications across your catalog simultaneously using **pandas**.
        """
    )

    model_options = {
        "BAN 517 Inventory Classification (Multicriteria)": "classification",
        "Economic Order Quantity (EOQ)": "eoq",
        "Safety Stock & Reorder Point": "safety_stock",
        "Periodic Review (P, S)": "periodic_review",
        "Newsvendor Model": "newsvendor",
    }

    selected_model_label = st.selectbox(
        "Select Inventory Model for Batch Analysis:",
        options=list(model_options.keys()),
        index=0,
    )
    model_type = model_options[selected_model_label]

    if model_type == "classification":
        with st.expander("📘 BAN 517 Inventory Classification Methodology Summary", expanded=False):
            st.markdown(
                """
                **Official BAN 517 Classification Rules:**
                1. **Criteria:** Evaluates catalog items independently on **Sales ($)** (65% weight) and **POS Hits** (35% weight).
                2. **Pareto Sorting:** Items are sorted descending by Sales ($) and independently by Hits to calculate cumulative contribution percentages.
                3. **Tier Thresholds:**
                   - **Class A:** 0% – 60% cumulative contribution (Score = 4)
                   - **Class B:** Above 60% through 80% (Score = 3)
                   - **Class C:** Above 80% through 90% (Score = 2)
                   - **Class D:** Above 90% through 100% (Score = 1)
                   *(Items are assigned strictly by their own calculated cumulative percentage; threshold-crossing items are not automatically promoted).*
                4. **Combined Weighted Score:**
                   $$\\text{Combined Weighted Score} = 0.65 \\times \\text{Sales Score} + 0.35 \\times \\text{Hits Score}$$
                5. **Final Class Boundaries:**
                   - **Class A:** Score $\\ge 3.25$
                   - **Class B:** $2.50 \\le \\text{Score} < 3.25$
                   - **Class C:** $1.75 \\le \\text{Score} < 2.50$
                   - **Class D:** Score $< 1.75$
                """
            )

    st.markdown("---")
    c_dl, c_up = st.columns([1, 2])

    with c_dl:
        st.subheader("1. Download Template")
        st.caption("Download the pre-formatted CSV template with sample data:")
        sample_csv_str = generate_sample_csv(model_type)
        st.download_button(
            label=f"⬇️ Download Template (.csv)",
            data=sample_csv_str,
            file_name=f"{model_type}_template.csv",
            mime="text/csv",
        )

        st.markdown("**Expected Columns:**")
        sample_df = SAMPLE_TEMPLATES[model_type]
        st.code(", ".join(sample_df.columns), language="text")

    with c_up:
        st.subheader("2. Upload Your CSV File")
        uploaded_file = st.file_uploader(
            f"Upload {selected_model_label} CSV",
            type=["csv"],
            help="Upload a CSV matching the required column format.",
        )

        use_sample = st.checkbox("Or test with built-in sample dataset", value=False)

    target_file = None
    if uploaded_file is not None:
        target_file = uploaded_file
    elif use_sample:
        target_file = io.StringIO(sample_csv_str)

    if target_file is not None:
        st.markdown("---")
        st.subheader("3. Batch Calculation Results")

        success, result_df, message = process_batch_csv(target_file, model_type)

        if not success:
            st.error(f"❌ {message}")
            return

        st.success(f"✅ {message}")

        # Summary KPIs & Tables based on model
        if model_type == "classification":
            summary_info = result_df.attrs.get("summary_info")

            if summary_info is not None:
                counts = summary_info["counts"]
                sales_by_cls = summary_info["sales_by_class"]
                total_s = summary_info["total_sales"]

                # 4 KPI Cards
                k1, k2, k3, k4 = st.columns(4)
                k1.metric(
                    "Class A Items",
                    f"{counts.get('A', 0):,} items",
                    f"${sales_by_cls.get('A', 0.0):,.2f} ({sales_by_cls.get('A', 0.0)/total_s*100:.1f}%)" if total_s > 0 else "$0.00",
                )
                k2.metric(
                    "Class B Items",
                    f"{counts.get('B', 0):,} items",
                    f"${sales_by_cls.get('B', 0.0):,.2f} ({sales_by_cls.get('B', 0.0)/total_s*100:.1f}%)" if total_s > 0 else "$0.00",
                )
                k3.metric(
                    "Class C Items",
                    f"{counts.get('C', 0):,} items",
                    f"${sales_by_cls.get('C', 0.0):,.2f} ({sales_by_cls.get('C', 0.0)/total_s*100:.1f}%)" if total_s > 0 else "$0.00",
                )
                k4.metric(
                    "Class D Items",
                    f"{counts.get('D', 0):,} items",
                    f"${sales_by_cls.get('D', 0.0):,.2f} ({sales_by_cls.get('D', 0.0)/total_s*100:.1f}%)" if total_s > 0 else "$0.00",
                )

                # Required Summary Table
                st.markdown("### 📊 Final Classification Category Summary")
                st.caption(
                    "Distribution of catalog items and total sales revenue across final multicriteria classes A, B, C, and D:"
                )

                summary_table_display = summary_info["summary_table"].copy()
                summary_table_display["Total Sales ($)"] = summary_table_display["Total Sales ($)"].apply(lambda x: f"${x:,.2f}")
                summary_table_display["% of Items"] = summary_table_display["% of Items"].apply(lambda x: f"{x:.2f}%")
                summary_table_display["% of Total Sales"] = summary_table_display["% of Total Sales"].apply(lambda x: f"{x:.2f}%")
                summary_table_display["Total Hits"] = summary_table_display["Total Hits"].apply(lambda x: f"{x:,}")
                summary_table_display["% of Total Hits"] = summary_table_display["% of Total Hits"].apply(lambda x: f"{x:.2f}%")

                st.dataframe(
                    summary_table_display[[
                        "Final Class",
                        "Number of Items",
                        "% of Items",
                        "Total Sales ($)",
                        "% of Total Sales",
                        "Total Hits",
                        "% of Total Hits",
                    ]],
                    use_container_width=True,
                    hide_index=True,
                )

                # Pareto Plot
                fig = plot_classification_distribution(summary_info["summary_table"])
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)

        elif model_type == "eoq" and "Total_Annual_Cost" in result_df.columns:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("SKUs Analyzed", len(result_df))
            k2.metric("Total Annual Inventory Cost", f"${result_df['Total_Annual_Cost'].sum():,.2f}")
            k3.metric("Total Annual Order Cost", f"${result_df['Annual_Ordering_Cost'].sum():,.2f}")
            k4.metric("Total Annual Holding Cost", f"${result_df['Annual_Holding_Cost'].sum():,.2f}")

        elif model_type == "safety_stock" and "Safety_Stock" in result_df.columns:
            k1, k2, k3 = st.columns(3)
            k1.metric("SKUs Analyzed", len(result_df))
            k2.metric("Total Safety Stock Units", f"{result_df['Safety_Stock'].sum():,.1f}")
            k3.metric("Average Reorder Point", f"{result_df['Reorder_Point'].mean():,.1f} units")

        elif model_type == "periodic_review" and "Recommended_Order_Qty" in result_df.columns:
            k1, k2, k3 = st.columns(3)
            k1.metric("SKUs Analyzed", len(result_df))
            k2.metric("Total Recommended Order", f"{result_df['Recommended_Order_Qty'].sum():,.0f} units")
            k3.metric("Total Inventory Position", f"{result_df['Inventory_Position'].sum():,.0f} units")

        elif model_type == "newsvendor" and "Expected_Profit" in result_df.columns:
            k1, k2, k3 = st.columns(3)
            k1.metric("SKUs Analyzed", len(result_df))
            k2.metric("Total Expected Profit", f"${result_df['Expected_Profit'].sum():,.2f}")
            k3.metric("Total Procured Units", f"{result_df['Optimal_Quantity'].sum():,.1f}")

        # Display Data Table
        st.markdown("### 📋 Enriched Catalog Results")
        st.dataframe(result_df, use_container_width=True)

        # Download Processed Results
        csv_buffer = io.StringIO()
        result_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="💾 Download Calculated Decisions as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"{model_type}_decisions_calculated.csv",
            mime="text/csv",
        )
