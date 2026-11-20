"""CSV batch processing and template generation utilities using pandas."""

from __future__ import annotations
import io
from typing import Dict, Any, Tuple
import pandas as pd

from core.eoq import calculate_eoq
from core.safety_stock_rop import calculate_safety_stock_rop, LTDUncertaintyMode
from core.periodic_review import calculate_periodic_review
from core.newsvendor import calculate_newsvendor
from core.classification import calculate_ban517_classification


SAMPLE_TEMPLATES = {
    "eoq": pd.DataFrame([
        {"SKU": "SKU-1001", "Annual_Demand": 12000, "Order_Cost": 75.0, "Unit_Cost": 25.0, "Holding_Rate": 0.20},
        {"SKU": "SKU-1002", "Annual_Demand": 4500, "Order_Cost": 120.0, "Unit_Cost": 60.0, "Holding_Rate": 0.25},
        {"SKU": "SKU-1003", "Annual_Demand": 28000, "Order_Cost": 50.0, "Unit_Cost": 8.5, "Holding_Rate": 0.18},
        {"SKU": "SKU-1004", "Annual_Demand": 900, "Order_Cost": 150.0, "Unit_Cost": 320.0, "Holding_Rate": 0.30},
    ]),
    "safety_stock": pd.DataFrame([
        {"SKU": "SKU-1001", "Mean_Daily_Demand": 40.0, "Std_Daily_Demand": 8.0, "Lead_Time_Days": 7.0, "Service_Level": 0.95},
        {"SKU": "SKU-1002", "Mean_Daily_Demand": 15.0, "Std_Daily_Demand": 4.5, "Lead_Time_Days": 14.0, "Service_Level": 0.98},
        {"SKU": "SKU-1003", "Mean_Daily_Demand": 95.0, "Std_Daily_Demand": 18.0, "Lead_Time_Days": 4.0, "Service_Level": 0.90},
        {"SKU": "SKU-1004", "Mean_Daily_Demand": 3.0, "Std_Daily_Demand": 1.2, "Lead_Time_Days": 21.0, "Service_Level": 0.99},
    ]),
    "periodic_review": pd.DataFrame([
        {"SKU": "SKU-1001", "Review_Period_Days": 7, "Lead_Time_Days": 5, "Mean_Daily_Demand": 35.0, "Std_Daily_Demand": 6.0, "Service_Level": 0.95, "On_Hand": 120, "On_Order": 50, "Backorders": 0},
        {"SKU": "SKU-1002", "Review_Period_Days": 14, "Lead_Time_Days": 10, "Mean_Daily_Demand": 12.0, "Std_Daily_Demand": 3.5, "Service_Level": 0.98, "On_Hand": 80, "On_Order": 0, "Backorders": 5},
        {"SKU": "SKU-1003", "Review_Period_Days": 7, "Lead_Time_Days": 3, "Mean_Daily_Demand": 80.0, "Std_Daily_Demand": 15.0, "Service_Level": 0.90, "On_Hand": 300, "On_Order": 200, "Backorders": 0},
    ]),
    "newsvendor": pd.DataFrame([
        {"SKU": "SEASONAL-01", "Selling_Price": 120.0, "Purchase_Cost": 50.0, "Salvage_Value": 20.0, "Mean_Demand": 500.0, "Std_Demand": 85.0},
        {"SKU": "SEASONAL-02", "Selling_Price": 75.0, "Purchase_Cost": 40.0, "Salvage_Value": 15.0, "Mean_Demand": 1200.0, "Std_Demand": 220.0},
        {"SKU": "SEASONAL-03", "Selling_Price": 250.0, "Purchase_Cost": 110.0, "Salvage_Value": 45.0, "Mean_Demand": 180.0, "Std_Demand": 40.0},
    ]),
    "classification": pd.DataFrame([
        {"Item Number": "1090", "Item Name": "Ipad", "UoM": "EA", "Sales ($)": 9328940, "Hits": 1780},
        {"Item Number": "1180", "Item Name": "Speaker-Bose", "UoM": "EA", "Sales ($)": 7202900, "Hits": 75},
        {"Item Number": "1055", "Item Name": "Dell Studio 17", "UoM": "EA", "Sales ($)": 7055100, "Hits": 83},
        {"Item Number": "1054", "Item Name": "Dell Studio 15", "UoM": "EA", "Sales ($)": 5761300, "Hits": 71},
        {"Item Number": "1083", "Item Name": "HP Pavilion dv7", "UoM": "EA", "Sales ($)": 4381000, "Hits": 64},
        {"Item Number": "1012", "Item Name": "Apple Macbook Pro", "UoM": "EA", "Sales ($)": 3942000, "Hits": 145},
        {"Item Number": "1195", "Item Name": "USB Cable 6ft", "UoM": "EA", "Sales ($)": 45000, "Hits": 890},
        {"Item Number": "1204", "Item Name": "Stylus Pen", "UoM": "EA", "Sales ($)": 12000, "Hits": 320},
    ]),
}


def generate_sample_csv(model_type: str) -> str:
    """Return a CSV string for a sample template."""
    df = SAMPLE_TEMPLATES.get(model_type.lower())
    if df is None:
        raise ValueError(f"Unknown model type '{model_type}'. Choose from {list(SAMPLE_TEMPLATES.keys())}")
    return df.to_csv(index=False)


def process_batch_csv(uploaded_file, model_type: str) -> Tuple[bool, Any, str]:
    """Parse and calculate inventory decisions for an uploaded CSV file.

    Returns:
        (success: bool, result_df_or_none, message: str)
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        return False, None, f"Failed to parse CSV file: {str(e)}"

    if df.empty:
        return False, None, "Uploaded CSV file is empty."

    # Normalize column names: trim whitespace and uppercase
    df.columns = [col.strip() for col in df.columns]

    model_type = model_type.lower()

    try:
        if model_type == "eoq":
            required = ["SKU", "Annual_Demand", "Order_Cost", "Unit_Cost", "Holding_Rate"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                return False, None, f"Missing required columns for EOQ: {missing}"

            def compute_row(row):
                res = calculate_eoq(
                    annual_demand=float(row["Annual_Demand"]),
                    order_cost=float(row["Order_Cost"]),
                    unit_cost=float(row["Unit_Cost"]),
                    holding_cost_rate=float(row["Holding_Rate"]),
                )
                return pd.Series({
                    "EOQ": round(res["eoq"], 1),
                    "Orders_Per_Year": round(res["orders_per_year"], 2),
                    "Cycle_Time_Days": round(res["cycle_time_days"], 1),
                    "Annual_Ordering_Cost": round(res["annual_ordering_cost"], 2),
                    "Annual_Holding_Cost": round(res["annual_holding_cost"], 2),
                    "Annual_Purchase_Cost": round(res["annual_purchasing_cost"], 2),
                    "Total_Annual_Cost": round(res["total_annual_cost"], 2),
                })

            calculated = df.apply(compute_row, axis=1)
            result_df = pd.concat([df, calculated], axis=1)
            return True, result_df, f"Successfully processed {len(result_df)} EOQ records."

        elif model_type == "safety_stock":
            required = ["SKU", "Mean_Daily_Demand", "Std_Daily_Demand", "Lead_Time_Days", "Service_Level"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                return False, None, f"Missing required columns for Safety Stock: {missing}"

            def compute_row(row):
                res = calculate_safety_stock_rop(
                    service_level=float(row["Service_Level"]),
                    mode=LTDUncertaintyMode.DEMAND_ONLY,
                    mean_demand=float(row["Mean_Daily_Demand"]),
                    std_demand=float(row["Std_Daily_Demand"]),
                    mean_lead_time=float(row["Lead_Time_Days"]),
                )
                return pd.Series({
                    "Z_Score": round(res["z_score"], 3),
                    "Lead_Time_Demand_Mean": round(res["mean_lead_time_demand"], 1),
                    "Lead_Time_Demand_Std": round(res["std_lead_time_demand"], 2),
                    "Safety_Stock": round(res["safety_stock"], 1),
                    "Reorder_Point": round(res["reorder_point"], 1),
                    "Reorder_Point_Ceil": res["reorder_point_rounded"],
                })

            calculated = df.apply(compute_row, axis=1)
            result_df = pd.concat([df, calculated], axis=1)
            return True, result_df, f"Successfully processed {len(result_df)} Safety Stock records."

        elif model_type == "periodic_review":
            required = ["SKU", "Review_Period_Days", "Lead_Time_Days", "Mean_Daily_Demand", "Std_Daily_Demand", "Service_Level", "On_Hand", "On_Order", "Backorders"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                return False, None, f"Missing required columns for Periodic Review: {missing}"

            def compute_row(row):
                res = calculate_periodic_review(
                    review_period=float(row["Review_Period_Days"]),
                    lead_time=float(row["Lead_Time_Days"]),
                    mean_demand_per_period=float(row["Mean_Daily_Demand"]),
                    std_demand_per_period=float(row["Std_Daily_Demand"]),
                    service_level=float(row["Service_Level"]),
                    on_hand_inventory=float(row["On_Hand"]),
                    on_order_inventory=float(row["On_Order"]),
                    backorders=float(row["Backorders"]),
                )
                return pd.Series({
                    "Protection_Interval_Days": res["protection_interval"],
                    "Safety_Stock": round(res["safety_stock_periodic"], 1),
                    "Order_Up_To_Level": round(res["order_up_to_level"], 1),
                    "Inventory_Position": res["inventory_position"],
                    "Recommended_Order_Qty": res["order_quantity_rounded"],
                })

            calculated = df.apply(compute_row, axis=1)
            result_df = pd.concat([df, calculated], axis=1)
            return True, result_df, f"Successfully processed {len(result_df)} Periodic Review records."

        elif model_type == "newsvendor":
            required = ["SKU", "Selling_Price", "Purchase_Cost", "Salvage_Value", "Mean_Demand", "Std_Demand"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                return False, None, f"Missing required columns for Newsvendor: {missing}"

            def compute_row(row):
                res = calculate_newsvendor(
                    selling_price=float(row["Selling_Price"]),
                    purchase_cost=float(row["Purchase_Cost"]),
                    salvage_value=float(row["Salvage_Value"]),
                    mean_demand=float(row["Mean_Demand"]),
                    std_demand=float(row["Std_Demand"]),
                )
                return pd.Series({
                    "Underage_Cost": round(res["underage_cost"], 2),
                    "Overage_Cost": round(res["overage_cost"], 2),
                    "Critical_Ratio": round(res["critical_ratio"], 4),
                    "Optimal_Quantity": round(res["optimal_quantity"], 1),
                    "Expected_Sales": round(res["expected_sales"], 1),
                    "Expected_Leftover": round(res["expected_leftover"], 1),
                    "Expected_Shortage": round(res["expected_shortage"], 2),
                    "Expected_Profit": round(res["expected_profit"], 2),
                })

            calculated = df.apply(compute_row, axis=1)
            result_df = pd.concat([df, calculated], axis=1)
            return True, result_df, f"Successfully processed {len(result_df)} Newsvendor records."

        elif model_type == "classification":
            result_df, summary_info = calculate_ban517_classification(df)
            result_df.attrs["summary_info"] = summary_info
            return True, result_df, f"Successfully classified {len(result_df)} inventory items using BAN 517 Methodology."

        else:
            return False, None, f"Unsupported model type '{model_type}'."

    except Exception as e:
        return False, None, f"Calculation error during processing: {str(e)}"
