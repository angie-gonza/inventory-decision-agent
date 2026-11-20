"""Safety Stock and Reorder Point (ROP) Model.

Calculates the buffer inventory required to protect against demand and/or lead time
uncertainty during the replenishment lead time under continuous review (s, S) or (R, Q).
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Dict, Any, Optional

try:
    from scipy.stats import norm
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def normal_ppf(p: float) -> float:
    """Standard normal percent point function (inverse CDF) Φ^(-1)(p).
    
    Uses scipy.stats.norm.ppf if available; otherwise uses Peter Acklam's high-precision algorithm.
    """
    if p <= 0.0 or p >= 1.0:
        raise ValueError("Probability p must be strictly between 0 and 1.")

    if HAS_SCIPY:
        return float(norm.ppf(p))

    # Acklam's approximation for Φ^(-1)(p) with error < 1.15e-9
    a = [-3.969683028665376e+01,  2.209460984245205e+02, -2.759285104469687e+02,
          1.383577518672690e+02, -3.066479806614716e+01,  2.506628277459239e+00]
    b = [-5.447609879822406e+01,  1.615858368580409e+02, -1.556989798598866e+02,
          6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00,  4.374664141464968e+00,  2.938163982698783e+00]
    d = [ 7.784695709041462e-03,  3.224671290700398e-01,  2.445134137142996e+00,
          3.754408661907416e+00]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5])*q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)


class LTDUncertaintyMode(str, Enum):
    """Lead Time Demand Uncertainty Scenarios."""
    DEMAND_ONLY = "stochastic_demand_constant_lead_time"
    LEAD_TIME_ONLY = "constant_demand_stochastic_lead_time"
    BOTH = "both_stochastic"


def calculate_safety_stock_rop(
    service_level: float,
    mode: LTDUncertaintyMode = LTDUncertaintyMode.DEMAND_ONLY,
    mean_demand: float = 0.0,
    std_demand: float = 0.0,
    mean_lead_time: float = 0.0,
    std_lead_time: float = 0.0,
) -> Dict[str, Any]:
    """Calculate Safety Stock and Reorder Point under continuous review.

    Args:
        service_level (CSL): Target cycle service level between 0.50 and 0.9999.
        mode: Uncertainty scenario (demand only, lead time only, or both).
        mean_demand: Expected demand per period (e.g., day or week).
        std_demand: Standard deviation of demand per period.
        mean_lead_time: Expected replenishment lead time in the same time units.
        std_lead_time: Standard deviation of lead time in the same time units.

    Returns:
        dict: Calculated safety stock, reorder point, z-score, and distribution parameters.
    """
    if not (0.50 <= service_level < 1.0):
        raise ValueError("Service level (CSL) must be in the range [0.50, 0.9999].")
    if mean_demand < 0:
        raise ValueError("Mean demand cannot be negative.")
    if mean_lead_time < 0:
        raise ValueError("Lead time cannot be negative.")

    z = normal_ppf(service_level)

    if mode == LTDUncertaintyMode.DEMAND_ONLY:
        if std_demand < 0:
            raise ValueError("Demand standard deviation cannot be negative.")
        if mean_lead_time <= 0:
            raise ValueError("Lead time must be positive.")
        
        mean_ltd = mean_demand * mean_lead_time
        std_ltd = std_demand * math.sqrt(mean_lead_time)
        case_desc = "Stochastic Demand with Constant Lead Time"
        formula_text = r"\sigma_{L} = \sigma_d \sqrt{L}"

    elif mode == LTDUncertaintyMode.LEAD_TIME_ONLY:
        if std_lead_time < 0:
            raise ValueError("Lead time standard deviation cannot be negative.")
        
        mean_ltd = mean_demand * mean_lead_time
        std_ltd = mean_demand * std_lead_time
        case_desc = "Constant Demand with Stochastic Lead Time"
        formula_text = r"\sigma_{L} = d \cdot \sigma_L"

    elif mode == LTDUncertaintyMode.BOTH:
        if std_demand < 0 or std_lead_time < 0:
            raise ValueError("Standard deviations cannot be negative.")
        
        mean_ltd = mean_demand * mean_lead_time
        # Independent random variables variance: E[L]*Var(D) + (E[D])^2*Var(L)
        variance_ltd = (mean_lead_time * (std_demand ** 2)) + ((mean_demand ** 2) * (std_lead_time ** 2))
        std_ltd = math.sqrt(variance_ltd)
        case_desc = "Both Demand and Lead Time are Stochastic (Independent)"
        formula_text = r"\sigma_{L} = \sqrt{\mu_L \sigma_d^2 + \mu_d^2 \sigma_L^2}"

    else:
        raise ValueError(f"Unknown uncertainty mode: {mode}")

    safety_stock = z * std_ltd
    reorder_point = mean_ltd + safety_stock
    stockout_probability = 1.0 - service_level

    return {
        "service_level": service_level,
        "mode": mode.value,
        "case_description": case_desc,
        "formula_text": formula_text,
        "z_score": z,
        "mean_demand": mean_demand,
        "std_demand": std_demand,
        "mean_lead_time": mean_lead_time,
        "std_lead_time": std_lead_time,
        "mean_lead_time_demand": mean_ltd,
        "std_lead_time_demand": std_ltd,
        "safety_stock": safety_stock,
        "safety_stock_rounded": math.ceil(safety_stock),
        "reorder_point": reorder_point,
        "reorder_point_rounded": math.ceil(reorder_point),
        "stockout_probability": stockout_probability,
    }
