"""Quantity Discount Analysis Model (All-Units Discount).

Evaluates supplier price breaks to determine the optimal order quantity that
minimizes total annual inventory cost (Purchasing + Ordering + Holding).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class PriceTier:
    """Represents a quantity discount pricing bracket."""
    tier_id: int
    min_qty: float
    max_qty: Optional[float]  # None indicates infinity (upper bracket)
    unit_price: float

    def contains(self, quantity: float) -> bool:
        """Check if a quantity falls within this price bracket."""
        if quantity < self.min_qty:
            return False
        if self.max_qty is not None and quantity >= self.max_qty:
            return False
        return True


def calculate_quantity_discount(
    annual_demand: float,
    order_cost: float,
    holding_cost_rate: float,
    price_tiers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate the optimal order quantity across all price discount tiers.

    Args:
        annual_demand (D): Annual demand in units (> 0).
        order_cost (S): Fixed cost per order ($ > 0).
        holding_cost_rate (h): Annual holding cost rate as a decimal (e.g. 0.20 for 20%).
        price_tiers: List of dicts with 'min_qty', 'max_qty' (or None), and 'unit_price'.

    Returns:
        dict: Evaluation for each tier, the optimal tier, optimal Q, and cost breakdown.
    """
    if annual_demand <= 0:
        raise ValueError("Annual demand (D) must be strictly positive.")
    if order_cost <= 0:
        raise ValueError("Order cost (S) must be strictly positive.")
    if holding_cost_rate <= 0:
        raise ValueError("Holding cost rate (h) must be strictly positive.")
    if not price_tiers:
        raise ValueError("At least one price tier must be provided.")

    # Validate and structure tiers
    structured_tiers: List[PriceTier] = []
    for i, t in enumerate(price_tiers):
        min_q = float(t["min_qty"])
        max_q = float(t["max_qty"]) if t.get("max_qty") is not None and t["max_qty"] != "" and not math.isinf(float(t["max_qty"])) else None
        price = float(t["unit_price"])

        if min_q < 0:
            raise ValueError(f"Tier {i+1}: min_qty cannot be negative.")
        if price <= 0:
            raise ValueError(f"Tier {i+1}: unit_price must be strictly positive.")
        if max_q is not None and max_q <= min_q:
            raise ValueError(f"Tier {i+1}: max_qty ({max_q}) must be greater than min_qty ({min_q}).")

        structured_tiers.append(PriceTier(tier_id=i + 1, min_qty=min_q, max_qty=max_q, unit_price=price))

    # Evaluate each tier
    tier_evaluations: List[Dict[str, Any]] = []

    for tier in structured_tiers:
        H_i = holding_cost_rate * tier.unit_price
        eoq_i = math.sqrt((2.0 * annual_demand * order_cost) / H_i)

        is_feasible_at_eoq = tier.contains(eoq_i)

        if is_feasible_at_eoq:
            candidate_q = eoq_i
            status = "Feasible at EOQ"
            is_valid_candidate = True
        elif eoq_i < tier.min_qty:
            candidate_q = tier.min_qty
            status = "Adjusted to Price Break Minimum"
            is_valid_candidate = True
        else:
            # eoq_i exceeds tier max_qty: higher tier will offer lower or equal cost
            candidate_q = tier.min_qty
            status = "Infeasible (EOQ exceeds bracket)"
            is_valid_candidate = False

        if is_valid_candidate:
            order_cost_ann = (annual_demand / candidate_q) * order_cost
            holding_cost_ann = (candidate_q / 2.0) * H_i
            purchase_cost_ann = annual_demand * tier.unit_price
            total_cost_ann = order_cost_ann + holding_cost_ann + purchase_cost_ann
            orders_per_yr = annual_demand / candidate_q
        else:
            order_cost_ann = None
            holding_cost_ann = None
            purchase_cost_ann = None
            total_cost_ann = None
            orders_per_yr = None

        tier_evaluations.append({
            "tier_id": tier.tier_id,
            "min_qty": tier.min_qty,
            "max_qty": tier.max_qty if tier.max_qty is not None else float("inf"),
            "unit_price": tier.unit_price,
            "holding_cost_unit": H_i,
            "calculated_eoq": eoq_i,
            "candidate_q": candidate_q,
            "status": status,
            "is_valid": is_valid_candidate,
            "annual_order_cost": order_cost_ann,
            "annual_holding_cost": holding_cost_ann,
            "annual_purchase_cost": purchase_cost_ann,
            "total_annual_cost": total_cost_ann,
            "orders_per_year": orders_per_yr,
        })

    # Find optimal candidate among valid ones
    valid_evals = [e for e in tier_evaluations if e["is_valid"] and e["total_annual_cost"] is not None]
    if not valid_evals:
        raise ValueError("Could not find any feasible order quantity among the provided price tiers.")

    best_eval = min(valid_evals, key=lambda x: x["total_annual_cost"])

    # Compute baseline comparison (tier 1 at EOQ or min_qty)
    baseline_cost = tier_evaluations[0]["total_annual_cost"]
    for ev in tier_evaluations:
        if ev["total_annual_cost"] is not None and baseline_cost is not None:
            ev["savings_vs_base"] = baseline_cost - ev["total_annual_cost"]
            ev["pct_savings_vs_base"] = (ev["savings_vs_base"] / baseline_cost) * 100.0
        else:
            ev["savings_vs_base"] = None
            ev["pct_savings_vs_base"] = None

    return {
        "annual_demand": annual_demand,
        "order_cost": order_cost,
        "holding_cost_rate": holding_cost_rate,
        "tier_evaluations": tier_evaluations,
        "optimal_tier_id": best_eval["tier_id"],
        "optimal_quantity": best_eval["candidate_q"],
        "optimal_unit_price": best_eval["unit_price"],
        "min_total_annual_cost": best_eval["total_annual_cost"],
        "optimal_annual_order_cost": best_eval["annual_order_cost"],
        "optimal_annual_holding_cost": best_eval["annual_holding_cost"],
        "optimal_annual_purchase_cost": best_eval["annual_purchase_cost"],
        "baseline_total_annual_cost": baseline_cost,
        "total_savings": baseline_cost - best_eval["total_annual_cost"] if baseline_cost else 0.0,
    }
