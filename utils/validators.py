"""Validation utilities for user inputs and data integrity."""

from typing import Tuple, Optional


def validate_positive(name: str, value: float, allow_zero: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate that a number is positive (or non-negative if allow_zero=True)."""
    if value is None:
        return False, f"'{name}' cannot be empty."
    if allow_zero:
        if value < 0:
            return False, f"'{name}' must be greater than or equal to 0 (received {value})."
    else:
        if value <= 0:
            return False, f"'{name}' must be strictly greater than 0 (received {value})."
    return True, None


def validate_range(
    name: str,
    value: float,
    min_val: float,
    max_val: float,
    include_min: bool = True,
    include_max: bool = True,
) -> Tuple[bool, Optional[str]]:
    """Validate that a number falls within a specified interval."""
    if value is None:
        return False, f"'{name}' cannot be empty."

    low_ok = (value >= min_val) if include_min else (value > min_val)
    high_ok = (value <= max_val) if include_max else (value < max_val)

    if not (low_ok and high_ok):
        lower_bracket = "[" if include_min else "("
        upper_bracket = "]" if include_max else ")"
        return False, f"'{name}' must be in the range {lower_bracket}{min_val}, {max_val}{upper_bracket} (received {value})."

    return True, None


def validate_percentage(name: str, value: float) -> Tuple[bool, Optional[str]]:
    """Validate a percentage expressed as a decimal in (0, 1) or [0, 1]."""
    return validate_range(name, value, 0.0001, 0.9999, include_min=True, include_max=True)
