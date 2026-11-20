"""Economic Order Quantity (EOQ) Model.

Calculates the optimal order quantity that minimizes the sum of annual ordering
and inventory holding costs under constant demand and deterministic conditions.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional


def calculate_eoq(
    annual_demand: float,
    order_cost: float,
    unit_cost: float,
    holding_cost_per_unit: Optional[float] = None,
    holding_cost_rate: Optional[float] = None,
    working_days_per_year: int = 250,
) -> Dict[str, Any]:
    """Calculate the Economic Order Quantity (EOQ) and associated cost metrics.

    Args:
        annual_demand (D): Total demand per year in units (must be > 0).
        order_cost (S): Fixed cost per order/setup in $ (must be > 0).
        unit_cost (C): Purchase cost per unit in $ (must be > 0).
        holding_cost_per_unit (H): Annual holding cost per unit in $/unit/year.
        holding_cost_rate (h): Holding cost fraction of unit cost per year (e.g., 0.20 for 20%).
        working_days_per_year: Operating days per year for cycle time in days (default 250).

    Returns:
        dict: Detailed calculated EOQ metrics, costs, and frequencies.
    """
    if annual_demand <= 0:
        raise ValueError("Annual demand (D) must be strictly positive.")
    if order_cost <= 0:
        raise ValueError("Order cost (S) must be strictly positive.")
    if unit_cost <= 0:
        raise ValueError("Unit cost (C) must be strictly positive.")

    # Determine holding cost per unit H
    if holding_cost_per_unit is not None and holding_cost_per_unit > 0:
        H = float(holding_cost_per_unit)
        h = H / unit_cost
    elif holding_cost_rate is not None and holding_cost_rate > 0:
        h = float(holding_cost_rate)
        H = h * unit_cost
    else:
        raise ValueError("Either holding_cost_per_unit (H > 0) or holding_cost_rate (h > 0) must be provided.")

    # Classical EOQ formula: sqrt(2 * D * S / H)
    eoq = math.sqrt((2.0 * annual_demand * order_cost) / H)

    # Operational metrics
    orders_per_year = annual_demand / eoq
    cycle_time_years = eoq / annual_demand
    cycle_time_days = cycle_time_years * working_days_per_year

    # Cost breakdown
    annual_ordering_cost = (annual_demand / eoq) * order_cost
    annual_holding_cost = (eoq / 2.0) * H
    annual_purchasing_cost = annual_demand * unit_cost
    total_variable_cost = annual_ordering_cost + annual_holding_cost
    total_annual_cost = total_variable_cost + annual_purchasing_cost

    return {
        "annual_demand": annual_demand,
        "order_cost": order_cost,
        "unit_cost": unit_cost,
        "holding_cost_per_unit": H,
        "holding_cost_rate": h,
        "working_days_per_year": working_days_per_year,
        "eoq": eoq,
        "eoq_rounded": round(eoq),
        "orders_per_year": orders_per_year,
        "cycle_time_years": cycle_time_years,
        "cycle_time_days": cycle_time_days,
        "annual_ordering_cost": annual_ordering_cost,
        "annual_holding_cost": annual_holding_cost,
        "annual_purchasing_cost": annual_purchasing_cost,
        "total_variable_cost": total_variable_cost,
        "total_annual_cost": total_annual_cost,
    }


def generate_eoq_cost_curve(
    annual_demand: float,
    order_cost: float,
    holding_cost_per_unit: float,
    min_q: Optional[float] = None,
    max_q: Optional[float] = None,
    points: int = 100,
) -> Dict[str, List[float]]:
    """Generate cost curves (Ordering, Holding, Total Variable Cost) over a range of order quantities.

    Returns:
        dict: Lists of Q, ordering_cost, holding_cost, total_variable_cost.
    """
    eoq = math.sqrt((2.0 * annual_demand * order_cost) / holding_cost_per_unit)
    
    if min_q is None or min_q <= 0:
        min_q = max(1.0, eoq * 0.2)
    if max_q is None or max_q <= min_q:
        max_q = eoq * 2.5

    step = (max_q - min_q) / (points - 1)
    q_values = [min_q + i * step for i in range(points)]

    ordering_costs = [(annual_demand / q) * order_cost for q in q_values]
    holding_costs = [(q / 2.0) * holding_cost_per_unit for q in q_values]
    total_variable_costs = [o + h for o, h in zip(ordering_costs, holding_costs)]

    return {
        "q_values": q_values,
        "ordering_costs": ordering_costs,
        "holding_costs": holding_costs,
        "total_variable_costs": total_variable_costs,
        "eoq": eoq,
        "min_total_cost": math.sqrt(2.0 * annual_demand * order_cost * holding_cost_per_unit),
    }


def calculate_eoq_sensitivity(
    annual_demand: float,
    order_cost: float,
    holding_cost_per_unit: float,
    actual_q: float,
) -> Dict[str, float]:
    """Calculate the cost impact / penalty of ordering a non-optimal quantity actual_q instead of EOQ."""
    eoq = math.sqrt((2.0 * annual_demand * order_cost) / holding_cost_per_unit)
    opt_tic = math.sqrt(2.0 * annual_demand * order_cost * holding_cost_per_unit)

    actual_ordering = (annual_demand / actual_q) * order_cost
    actual_holding = (actual_q / 2.0) * holding_cost_per_unit
    actual_tic = actual_ordering + actual_holding

    cost_difference = actual_tic - opt_tic
    percentage_penalty = (cost_difference / opt_tic) * 100.0 if opt_tic > 0 else 0.0

    return {
        "eoq": eoq,
        "optimal_tic": opt_tic,
        "actual_q": actual_q,
        "actual_tic": actual_tic,
        "cost_difference": cost_difference,
        "percentage_penalty": percentage_penalty,
    }
