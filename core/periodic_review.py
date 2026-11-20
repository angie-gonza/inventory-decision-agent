"""Fixed-Period Review (Periodic Review) Model.

Calculates the Order-Up-To Level (OUL / Target S) and recommended replenishment order quantity
under a periodic review policy (P, S) where inventory is reviewed at regular intervals of length P.
"""

from __future__ import annotations
import math
from typing import Dict, Any
from .safety_stock_rop import normal_ppf


def calculate_periodic_review(
    review_period: float,
    lead_time: float,
    mean_demand_per_period: float,
    std_demand_per_period: float,
    service_level: float,
    on_hand_inventory: float = 0.0,
    on_order_inventory: float = 0.0,
    backorders: float = 0.0,
) -> Dict[str, Any]:
    """Calculate the Order-Up-To Level (S) and recommended order quantity for periodic review.

    Args:
        review_period (P): Review interval in periods/days (> 0).
        lead_time (L): Replenishment lead time in the same time units (>= 0).
        mean_demand_per_period: Average demand per period/day (> 0).
        std_demand_per_period: Standard deviation of demand per period/day (>= 0).
        service_level (CSL): Cycle service level between 0.50 and 0.9999.
        on_hand_inventory: Physical inventory currently on shelves (>= 0).
        on_order_inventory: Pending open replenishment orders in-transit (>= 0).
        backorders: Unfulfilled customer orders waiting to be delivered (>= 0).

    Returns:
        dict: Protection interval, Order-Up-To Level, inventory position, and recommended order.
    """
    if review_period <= 0:
        raise ValueError("Review period (P) must be strictly positive.")
    if lead_time < 0:
        raise ValueError("Lead time (L) cannot be negative.")
    if mean_demand_per_period < 0:
        raise ValueError("Mean demand cannot be negative.")
    if std_demand_per_period < 0:
        raise ValueError("Demand standard deviation cannot be negative.")
    if not (0.50 <= service_level < 1.0):
        raise ValueError("Service level (CSL) must be in the range [0.50, 0.9999].")
    if on_hand_inventory < 0:
        raise ValueError("On-hand inventory cannot be negative.")
    if on_order_inventory < 0:
        raise ValueError("On-order inventory cannot be negative.")
    if backorders < 0:
        raise ValueError("Backorders cannot be negative.")

    # Total protection interval = Review Period (P) + Lead Time (L)
    protection_interval = review_period + lead_time

    # Normal z-score
    z = normal_ppf(service_level)

    # Demand over protection interval
    mean_protection_demand = mean_demand_per_period * protection_interval
    std_protection_demand = std_demand_per_period * math.sqrt(protection_interval)

    # Safety stock for periodic review
    safety_stock_periodic = z * std_protection_demand

    # Order-Up-To Level (OUL / Target S)
    order_up_to_level = mean_protection_demand + safety_stock_periodic

    # Current Inventory Position = On-Hand + On-Order - Backorders
    inventory_position = on_hand_inventory + on_order_inventory - backorders

    # Recommended Order Quantity = max(0, OUL - IP)
    order_quantity = max(0.0, order_up_to_level - inventory_position)

    # Continuous Review Comparison for Safety Stock (over lead time L only)
    if lead_time > 0:
        continuous_std_ltd = std_demand_per_period * math.sqrt(lead_time)
        continuous_safety_stock = z * continuous_std_ltd
        safety_stock_increase_pct = (
            ((safety_stock_periodic - continuous_safety_stock) / continuous_safety_stock) * 100.0
            if continuous_safety_stock > 0 else 0.0
        )
    else:
        continuous_safety_stock = 0.0
        safety_stock_increase_pct = 100.0 if safety_stock_periodic > 0 else 0.0

    return {
        "review_period": review_period,
        "lead_time": lead_time,
        "protection_interval": protection_interval,
        "mean_demand_per_period": mean_demand_per_period,
        "std_demand_per_period": std_demand_per_period,
        "service_level": service_level,
        "z_score": z,
        "mean_protection_demand": mean_protection_demand,
        "std_protection_demand": std_protection_demand,
        "safety_stock_periodic": safety_stock_periodic,
        "safety_stock_periodic_rounded": math.ceil(safety_stock_periodic),
        "order_up_to_level": order_up_to_level,
        "order_up_to_level_rounded": math.ceil(order_up_to_level),
        "on_hand_inventory": on_hand_inventory,
        "on_order_inventory": on_order_inventory,
        "backorders": backorders,
        "inventory_position": inventory_position,
        "order_quantity": order_quantity,
        "order_quantity_rounded": math.ceil(order_quantity),
        "continuous_safety_stock": continuous_safety_stock,
        "safety_stock_increase_pct": safety_stock_increase_pct,
    }
