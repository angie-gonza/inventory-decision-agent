"""BAN 517 Multicriteria Inventory Classification Module.

Implements the official BAN 517 Inventory Analytics methodology:
- Independent Pareto ranking by Sales ($) and POS Hits.
- Cumulative percentage threshold classification (A: 0-60%, B: >60-80%, C: >80-90%, D: >90-100%).
- Numerical scoring (A=4, B=3, C=2, D=1).
- Combined Weighted Score = 0.65 * Sales Score + 0.35 * Hits Score.
- Final Class boundaries: A (>= 3.25), B (>= 2.50 to < 3.25), C (>= 1.75 to < 2.50), D (< 1.75).
"""

from __future__ import annotations
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np


SCORE_MAP = {
    "A": 4,
    "B": 3,
    "C": 2,
    "D": 1,
}

WEIGHT_SALES = 0.65
WEIGHT_HITS = 0.35

CUTOFF_A = 3.25
CUTOFF_B = 2.50
CUTOFF_C = 1.75


def assign_tier_from_cum_pct(cum_pct: float) -> Tuple[str, int]:
    """Assign letter class and numerical score based on calculated cumulative percentage.

    Threshold rules:
      - A: 0% to 60% (inclusive of 60%)
      - B: above 60% through 80% (inclusive of 80%)
      - C: above 80% through 90% (inclusive of 90%)
      - D: above 90% through 100%

    Note: Each item is classified by its own calculated cumulative percentage.
    Threshold-crossing items are NOT automatically promoted to the higher class.
    """
    if cum_pct <= 60.0:
        return "A", 4
    elif cum_pct <= 80.0:
        return "B", 3
    elif cum_pct <= 90.0:
        return "C", 2
    else:
        return "D", 1


def assign_final_class_from_score(score: float) -> str:
    """Assign the final inventory classification based on Combined Weighted Score.

    Cutoff rules:
      - A: Score >= 3.25
      - B: Score >= 2.50 and < 3.25
      - C: Score >= 1.75 and < 2.50
      - D: Score < 1.75
    """
    if score >= CUTOFF_A:
        return "A"
    elif score >= CUTOFF_B:
        return "B"
    elif score >= CUTOFF_C:
        return "C"
    else:
        return "D"


def identify_columns(df: pd.DataFrame) -> Tuple[str, str]:
    """Identify Sales and Hits column names flexibly."""
    cols_clean = {c.strip().lower(): c for c in df.columns}

    # Match Sales column
    sales_col = None
    for candidate in ["sales ($)", "sales", "sales$", "sales_usd", "annual_sales"]:
        if candidate in cols_clean:
            sales_col = cols_clean[candidate]
            break

    # Match Hits column
    hits_col = None
    for candidate in ["hits", "pos hits", "pos_hits", "poshits", "order_hits"]:
        if candidate in cols_clean:
            hits_col = cols_clean[candidate]
            break

    if not sales_col:
        raise ValueError("Could not find a 'Sales ($)' or 'Sales' column in the uploaded dataset.")
    if not hits_col:
        raise ValueError("Could not find a 'Hits' or 'POS Hits' column in the uploaded dataset.")

    return sales_col, hits_col


def clean_numeric_series(series: pd.Series, col_name: str) -> pd.Series:
    """Clean and convert series to float, removing currency symbols and commas."""
    if pd.api.types.is_numeric_dtype(series):
        numeric = series.astype(float)
    else:
        # String cleanup: remove $, commas, whitespace
        cleaned = series.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False).str.strip()
        numeric = pd.to_numeric(cleaned, errors="coerce")

    if numeric.isna().any():
        bad_count = numeric.isna().sum()
        raise ValueError(f"Column '{col_name}' contains {bad_count} non-numeric or missing value(s).")

    if (numeric < 0).any():
        neg_count = (numeric < 0).sum()
        raise ValueError(f"Column '{col_name}' contains {neg_count} negative value(s). Values must be non-negative.")

    return numeric


def calculate_ban517_classification(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Perform BAN 517 Multicriteria Inventory Classification on the supplied DataFrame.

    Returns:
        (enriched_df, summary_metrics)
    """
    if df is None or df.empty:
        raise ValueError("The provided dataset is empty.")

    result_df = df.copy()

    # Identify columns
    sales_col, hits_col = identify_columns(result_df)

    # Sanitize and extract numeric vectors
    sales_clean = clean_numeric_series(result_df[sales_col], sales_col)
    hits_clean = clean_numeric_series(result_df[hits_col], hits_col)

    total_sales = float(sales_clean.sum())
    total_hits = float(hits_clean.sum())

    if total_sales <= 0:
        raise ValueError(f"Total {sales_col} is {total_sales}. Total sales must be strictly greater than 0.")
    if total_hits <= 0:
        raise ValueError(f"Total {hits_col} is {total_hits}. Total hits must be strictly greater than 0.")

    result_df["_temp_sales"] = sales_clean
    result_df["_temp_hits"] = hits_clean
    result_df["_orig_order"] = np.arange(len(result_df))

    # --- 1. Independent Sorting by Sales ($) ---
    df_by_sales = result_df.sort_values(by=["_temp_sales", "_temp_hits"], ascending=[False, False]).copy()
    sales_cumsum = df_by_sales["_temp_sales"].cumsum()
    df_by_sales["Sales_Cum_Pct"] = (sales_cumsum / total_sales) * 100.0

    sales_classes = []
    sales_scores = []
    for cp in df_by_sales["Sales_Cum_Pct"]:
        c, s = assign_tier_from_cum_pct(cp)
        sales_classes.append(c)
        sales_scores.append(s)

    df_by_sales["Sales_Class"] = sales_classes
    df_by_sales["Sales_Score"] = sales_scores

    # --- 2. Independent Sorting by Hits ---
    df_by_hits = result_df.sort_values(by=["_temp_hits", "_temp_sales"], ascending=[False, False]).copy()
    hits_cumsum = df_by_hits["_temp_hits"].cumsum()
    df_by_hits["Hits_Cum_Pct"] = (hits_cumsum / total_hits) * 100.0

    hits_classes = []
    hits_scores = []
    for cp in df_by_hits["Hits_Cum_Pct"]:
        c, s = assign_tier_from_cum_pct(cp)
        hits_classes.append(c)
        hits_scores.append(s)

    df_by_hits["Hits_Class"] = hits_classes
    df_by_hits["Hits_Score"] = hits_scores

    # --- 3. Recombine by original index ---
    sales_part = df_by_sales[["_orig_order", "Sales_Cum_Pct", "Sales_Class", "Sales_Score"]].set_index("_orig_order")
    hits_part = df_by_hits[["_orig_order", "Hits_Cum_Pct", "Hits_Class", "Hits_Score"]].set_index("_orig_order")

    combined = result_df.set_index("_orig_order").join(sales_part).join(hits_part)

    # --- 4. Combined Weighted Score: 0.65 * Sales_Score + 0.35 * Hits_Score ---
    combined["Combined_Weighted_Score"] = (
        (WEIGHT_SALES * combined["Sales_Score"]) + (WEIGHT_HITS * combined["Hits_Score"])
    ).round(4)

    # --- 5. Final Class Assignment ---
    combined["Final_Class"] = combined["Combined_Weighted_Score"].apply(assign_final_class_from_score)

    # Clean up temporary helper columns
    combined.drop(columns=["_temp_sales", "_temp_hits"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    # Round cumulative percentages to 2 decimals for clean display/export
    combined["Sales_Cum_Pct"] = combined["Sales_Cum_Pct"].round(2)
    combined["Hits_Cum_Pct"] = combined["Hits_Cum_Pct"].round(2)

    # --- 6. Summary Metrics: Item Count and Total Sales ($) by Final Class ---
    summary_rows = []
    total_items = len(combined)

    for cls in ["A", "B", "C", "D"]:
        subset = combined[combined["Final_Class"] == cls]
        count = len(subset)
        sales_sum = float(subset[sales_col].astype(float).sum()) if count > 0 else 0.0
        hits_sum = float(subset[hits_col].astype(float).sum()) if count > 0 else 0.0

        summary_rows.append({
            "Final Class": f"Class {cls}",
            "Class Code": cls,
            "Number of Items": count,
            "% of Items": round((count / total_items) * 100.0, 2) if total_items > 0 else 0.0,
            "Total Sales ($)": sales_sum,
            "% of Total Sales": round((sales_sum / total_sales) * 100.0, 2) if total_sales > 0 else 0.0,
            "Total Hits": int(hits_sum),
            "% of Total Hits": round((hits_sum / total_hits) * 100.0, 2) if total_hits > 0 else 0.0,
        })

    summary_df = pd.DataFrame(summary_rows)

    summary_info = {
        "total_items": total_items,
        "total_sales": total_sales,
        "total_hits": total_hits,
        "sales_column": sales_col,
        "hits_column": hits_col,
        "summary_table": summary_df,
        "counts": {r["Class Code"]: r["Number of Items"] for r in summary_rows},
        "sales_by_class": {r["Class Code"]: r["Total Sales ($)"] for r in summary_rows},
    }

    return combined, summary_info
