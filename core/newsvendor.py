"""Newsvendor (Single-Period) Inventory Model.

Calculates the optimal stocking quantity for perishable or seasonal goods with uncertain demand
balancing the marginal cost of overstocking against the marginal cost of understocking.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional
from .safety_stock_rop import normal_ppf

try:
    from scipy.stats import norm
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def normal_pdf(z: float) -> float:
    """Standard normal probability density function φ(z)."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * z * z)


def normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution function Φ(z)."""
    if HAS_SCIPY:
        return float(norm.cdf(z))
    # Approximation using error function
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def standard_normal_loss(z: float) -> float:
    """Standard normal unit loss function L(z) = φ(z) - z * (1 - Φ(z)).
    
    Represents the expected shortage for N(0, 1) when ordering at quantile z.
    """
    phi = normal_pdf(z)
    Phi = normal_cdf(z)
    return phi - z * (1.0 - Phi)


def calculate_newsvendor(
    selling_price: float,
    purchase_cost: float,
    salvage_value: float,
    mean_demand: float,
    std_demand: float,
    shortage_penalty: float = 0.0,
) -> Dict[str, Any]:
    """Calculate the Newsvendor optimal order quantity and financial expectations.

    Args:
        selling_price (P): Revenue per unit sold ($).
        purchase_cost (C): Cost per unit purchased ($).
        salvage_value (V): Net salvage or markdown value per unsold unit ($).
        mean_demand (μ): Expected demand for the single selling period.
        std_demand (σ): Standard deviation of demand.
        shortage_penalty (g): Additional goodwill or penalty cost per unit of unsatisfied demand (default 0).

    Returns:
        dict: Critical ratio, optimal quantity Q*, expected sales, leftover, shortage, and profit.
    """
    if selling_price <= 0:
        raise ValueError("Selling price (P) must be strictly positive.")
    if purchase_cost <= 0:
        raise ValueError("Purchase cost (C) must be strictly positive.")
    if salvage_value < 0:
        raise ValueError("Salvage value (V) cannot be negative.")
    if purchase_cost <= salvage_value:
        raise ValueError("Purchase cost (C) must be strictly greater than salvage value (V).")
    if selling_price <= purchase_cost:
        raise ValueError("Selling price (P) must be strictly greater than purchase cost (C).")
    if mean_demand < 0:
        raise ValueError("Mean demand cannot be negative.")
    if std_demand <= 0:
        raise ValueError("Standard deviation of demand must be strictly positive.")
    if shortage_penalty < 0:
        raise ValueError("Shortage penalty cannot be negative.")

    # Underage Cost: Cu = P - C + g
    underage_cost = selling_price - purchase_cost + shortage_penalty

    # Overage Cost: Co = C - V
    overage_cost = purchase_cost - salvage_value

    # Critical Ratio (Critical Fractile) = Cu / (Cu + Co)
    critical_ratio = underage_cost / (underage_cost + overage_cost)

    # Optimal z-score
    z_star = normal_ppf(critical_ratio)

    # Optimal Order Quantity: Q* = μ + z* * σ
    optimal_quantity = mean_demand + (z_star * std_demand)

    # Ensure non-negative order quantity
    optimal_quantity = max(0.0, optimal_quantity)

    # Expected shortage (lost sales)
    z_for_eval = (optimal_quantity - mean_demand) / std_demand
    unit_loss = standard_normal_loss(z_for_eval)
    expected_shortage = std_demand * unit_loss

    # Expected leftover units
    expected_leftover = optimal_quantity - mean_demand + expected_shortage

    # Expected units sold
    expected_sales = mean_demand - expected_shortage

    # Financial breakdown
    expected_revenue = (selling_price * expected_sales) + (salvage_value * expected_leftover)
    total_procurement_cost = purchase_cost * optimal_quantity
    expected_shortage_cost = shortage_penalty * expected_shortage
    expected_profit = expected_revenue - total_procurement_cost - expected_shortage_cost

    # Expected Profit under Perfect Information
    expected_profit_perfect_info = (selling_price - purchase_cost) * mean_demand
    evpi = max(0.0, expected_profit_perfect_info - expected_profit)

    return {
        "selling_price": selling_price,
        "purchase_cost": purchase_cost,
        "salvage_value": salvage_value,
        "shortage_penalty": shortage_penalty,
        "mean_demand": mean_demand,
        "std_demand": std_demand,
        "underage_cost": underage_cost,
        "overage_cost": overage_cost,
        "critical_ratio": critical_ratio,
        "z_star": z_star,
        "optimal_quantity": optimal_quantity,
        "optimal_quantity_rounded": round(optimal_quantity),
        "expected_sales": expected_sales,
        "expected_leftover": expected_leftover,
        "expected_shortage": expected_shortage,
        "expected_revenue": expected_revenue,
        "total_procurement_cost": total_procurement_cost,
        "expected_profit": expected_profit,
        "expected_profit_perfect_info": expected_profit_perfect_info,
        "evpi": evpi,
        "in_stock_probability": critical_ratio,
    }


def generate_newsvendor_profit_curve(
    selling_price: float,
    purchase_cost: float,
    salvage_value: float,
    mean_demand: float,
    std_demand: float,
    shortage_penalty: float = 0.0,
    points: int = 60,
) -> Dict[str, List[float]]:
    """Generate expected profit curve as a function of order quantity Q."""
    opt_res = calculate_newsvendor(
        selling_price=selling_price,
        purchase_cost=purchase_cost,
        salvage_value=salvage_value,
        mean_demand=mean_demand,
        std_demand=std_demand,
        shortage_penalty=shortage_penalty,
    )
    q_opt = opt_res["optimal_quantity"]

    min_q = max(0.0, mean_demand - 3.0 * std_demand)
    max_q = mean_demand + 3.5 * std_demand
    step = (max_q - min_q) / (points - 1)

    q_list: List[float] = [min_q + i * step for i in range(points)]
    profit_list: List[float] = []

    for q in q_list:
        z = (q - mean_demand) / std_demand
        u_loss = standard_normal_loss(z)
        shortage = std_demand * u_loss
        leftover = q - mean_demand + shortage
        sales = mean_demand - shortage
        rev = (selling_price * sales) + (salvage_value * leftover)
        cost = purchase_cost * q + shortage_penalty * shortage
        profit_list.append(rev - cost)

    return {
        "q_values": q_list,
        "expected_profits": profit_list,
        "optimal_q": q_opt,
        "max_profit": opt_res["expected_profit"],
    }
